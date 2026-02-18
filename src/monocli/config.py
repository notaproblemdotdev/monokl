"""Configuration management for monocli.

Reads configuration from environment variables and config files.
Priority: environment variables > keyring > config file > defaults
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from monocli import get_logger
from monocli import keyring_utils
from monocli.config_models import AppConfig

logger = get_logger(__name__)

# Default config locations (in priority order)
CONFIG_PATHS = [
    Path.home() / ".config" / "monocli" / "config.yaml",
    Path.home() / ".monocli.yaml",
    Path.cwd() / ".monocli.yaml",
]

# Default cache TTL in seconds (5 minutes)
DEFAULT_CACHE_TTL = 300

# Default cache cleanup threshold in days
DEFAULT_CACHE_CLEANUP_DAYS = 30


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


class Config:
    """Configuration manager for monocli.

    Loads configuration from environment variables and YAML config files.
    Environment variables take precedence over config file values.

    Environment variables:
        MONOCLI_GITLAB_GROUP: Default GitLab group to fetch MRs from
        MONOCLI_JIRA_PROJECT: Default Jira project to fetch issues from
        MONOCLI_TODOIST_TOKEN: Todoist API token

    Config file format (YAML):
        gitlab:
          group: "my-group"  # Default group for MR queries
        jira:
          project: "PROJ"    # Default project for issue queries
        todoist:
          token: "your-api-token"
          projects: ["Work", "Personal"]
          show_completed: false
          show_completed_for_last: "7days"

    Example:
        config = Config.load()
        group = config.gitlab_group  # Returns env var or config file value
    """

    def __init__(self, model: AppConfig) -> None:
        """Initialize config with Pydantic model.

        Args:
            model: Validated AppConfig instance.
        """
        self._model = model

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """Load configuration from file and environment.

        Args:
            path: Optional explicit config file path. If not provided,
                  searches default locations.

        Returns:
            Config instance with loaded settings.
        """
        data: dict[str, Any] = {}

        if path:
            data = cls._load_file(path)
        else:
            for config_path in CONFIG_PATHS:
                if config_path.exists():
                    logger.debug("Loading config from", path=str(config_path))
                    data = cls._load_file(config_path)
                    break

        data = cls._apply_env_vars(data)

        model = AppConfig.from_dict(data)
        return cls(model)

    @classmethod
    def _load_file(cls, path: Path) -> dict[str, Any]:
        """Load YAML config file.

        Args:
            path: Path to YAML config file.

        Returns:
            Dictionary with configuration values.
        """
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Failed to load config file", path=str(path), error=str(e))
            return {}

    @classmethod
    def _apply_env_vars(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides.

        Args:
            data: Current configuration dictionary.

        Returns:
            Updated dictionary with env var overrides.
        """
        # Ensure nested dicts exist
        if "gitlab" not in data:
            data["gitlab"] = {}
        if "jira" not in data:
            data["jira"] = {}
        if "todoist" not in data:
            data["todoist"] = {}
        if "cache" not in data:
            data["cache"] = {}

        # GitLab settings
        gitlab_group = os.getenv("MONOCLI_GITLAB_GROUP")
        if gitlab_group:
            data["gitlab"]["group"] = gitlab_group

        # Jira settings
        jira_project = os.getenv("MONOCLI_JIRA_PROJECT")
        if jira_project:
            data["jira"]["project"] = jira_project
        jira_base_url = os.getenv("MONOCLI_JIRA_BASE_URL")
        if jira_base_url:
            data["jira"]["base_url"] = jira_base_url

        # Todoist settings
        todoist_token = os.getenv("MONOCLI_TODOIST_TOKEN")
        if todoist_token:
            data["todoist"]["token"] = todoist_token

        # Cache/Database settings from environment
        db_path = os.getenv("MONOCLI_DB_PATH")
        if db_path:
            data["cache"]["db_path"] = db_path

        cache_ttl = os.getenv("MONOCLI_CACHE_TTL")
        if cache_ttl:
            try:
                data["cache"]["ttl_seconds"] = int(cache_ttl)
            except ValueError:
                pass

        return data

    @property
    def gitlab_group(self) -> str | None:
        """Get the configured GitLab group."""
        return self._model.gitlab.group

    @property
    def jira_project(self) -> str | None:
        """Get the configured Jira project."""
        return self._model.jira.project

    @property
    def jira_base_url(self) -> str | None:
        """Get the configured Jira base URL."""
        return self._model.jira.base_url

    @property
    def todoist_token(self) -> str | None:
        """Get the configured Todoist API token.

        Checks in priority order:
        1. Environment variable MONOCLI_TODOIST_TOKEN (highest priority)
        2. System keyring (secure storage)
        3. Config file (legacy, auto-migrates to keyring)

        Returns:
            Todoist API token or None if not configured.
        """
        env_token = os.getenv("MONOCLI_TODOIST_TOKEN")
        if env_token:
            return env_token

        keyring_token = keyring_utils.get_token("todoist")
        if keyring_token:
            return keyring_token

        config_token = self._model.todoist.token
        if config_token:
            self._migrate_todoist_token_to_keyring(config_token)
            return config_token

        return None

    @property
    def todoist_projects(self) -> list[str]:
        """Get the configured Todoist project filter list."""
        return self._model.todoist.projects

    @property
    def todoist_show_completed(self) -> bool:
        """Get whether to include completed Todoist tasks."""
        return self._model.todoist.show_completed

    @property
    def todoist_show_completed_for_last(self) -> str | None:
        """Get the timeframe for completed Todoist tasks.

        Returns:
            Timeframe string ("24h", "48h", "72h", "7days") or None.
        """
        value = self._model.todoist.show_completed_for_last
        return value.value if value else None

    @property
    def db_path(self) -> str | None:
        """Get the database path from environment or config."""
        env_path = os.getenv("MONOCLI_DB_PATH")
        if env_path:
            return env_path
        return self._model.cache.db_path

    @property
    def cache_ttl(self) -> int:
        """Get the cache TTL in seconds."""
        env_ttl = os.getenv("MONOCLI_CACHE_TTL")
        if env_ttl:
            try:
                return int(env_ttl)
            except ValueError:
                logger.warning("Invalid MONOCLI_CACHE_TTL value", value=env_ttl)
        return self._model.cache.ttl_seconds

    @property
    def offline_mode(self) -> bool:
        """Get whether offline mode is enabled."""
        return os.getenv("MONOCLI_OFFLINE_MODE", "").lower() in ("true", "1", "yes")

    @property
    def cache_cleanup_days(self) -> int:
        """Get the cache cleanup threshold in days."""
        return self._model.cache.cleanup_days

    @property
    def show_logs_command(self) -> str:
        """Get the command to view log files."""
        return self._model.dev.show_logs_command

    @property
    def preserve_sort_preference(self) -> bool:
        """Get whether to persist sort preferences across sessions."""
        return self._model.ui.preserve_sort_preference

    def get_config_path(self) -> Path | None:
        """Get the path to the config file being used.

        Returns:
            Path to config file, or None if no config file exists.
        """
        for config_path in CONFIG_PATHS:
            if config_path.exists():
                return config_path
        return None

    def _ensure_config_dir(self) -> Path:
        """Ensure config directory exists and return preferred config path.

        Returns:
            Path to the primary config file location.
        """
        config_path = CONFIG_PATHS[0]
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return config_path

    def _read_config_file(self) -> dict[str, Any]:
        """Read current config file contents.

        Returns:
            Config dictionary, or empty dict if file doesn't exist.
        """
        config_path = self.get_config_path()
        if not config_path or not config_path.exists():
            return {}
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Failed to read config file", error=str(e))
            return {}

    def _write_config_file(self, data: dict[str, Any]) -> bool:
        """Atomically write config file.

        Uses write-to-temp-then-rename pattern for atomicity.

        Args:
            data: Config dictionary to write

        Returns:
            True if successful, False otherwise
        """
        config_path = self._ensure_config_dir()

        try:
            temp_fd, temp_path = tempfile.mkstemp(
                dir=config_path.parent,
                prefix=".monocli-config-",
                suffix=".yaml",
            )
            try:
                with os.fdopen(temp_fd, "w") as f:
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
                os.replace(temp_path, config_path)
                self._model = AppConfig.from_dict(data)
                return True
            except Exception:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        except Exception as e:
            logger.error("Failed to write config file", error=str(e))
            return False

    def get_selected_adapter(self, integration: str) -> str | None:
        """Get the selected adapter type for an integration.

        Args:
            integration: Integration ID (e.g., "gitlab", "jira")

        Returns:
            Adapter type ("cli" or "api") or None if not selected
        """
        adapter = getattr(self._model.adapters, integration, None)
        if adapter:
            return adapter.selected
        return None

    def set_selected_adapter(self, integration: str, adapter_type: str) -> bool:
        """Set the selected adapter type for an integration.

        Args:
            integration: Integration ID (e.g., "gitlab", "jira")
            adapter_type: Adapter type ("cli" or "api")

        Returns:
            True if successful, False otherwise
        """
        data = self._read_config_file()

        if "adapters" not in data:
            data["adapters"] = {}
        if integration not in data["adapters"]:
            data["adapters"][integration] = {}
        if adapter_type not in data["adapters"][integration]:
            data["adapters"][integration][adapter_type] = {}

        data["adapters"][integration]["selected"] = adapter_type

        return self._write_config_file(data)

    def get_adapter_config(self, integration: str, adapter_type: str) -> dict[str, Any]:
        """Get configuration for a specific adapter.

        Returns non-secret config from YAML file. Use get_adapter_secret()
        for secret values stored in keyring.

        Args:
            integration: Integration ID (e.g., "gitlab", "jira")
            adapter_type: Adapter type ("cli" or "api")

        Returns:
            Adapter configuration dictionary (non-secret values only)
        """
        adapter = getattr(self._model.adapters, integration, None)
        if adapter:
            config = getattr(adapter, adapter_type, None)
            if config:
                return dict(config)
        return {}

    def set_adapter_config(
        self,
        integration: str,
        adapter_type: str,
        config: dict[str, Any],
        secrets: dict[str, str] | None = None,
    ) -> bool:
        """Set configuration for a specific adapter.

        Stores non-secret config in YAML file and secrets in keyring.

        Args:
            integration: Integration ID (e.g., "gitlab", "jira")
            adapter_type: Adapter type ("cli" or "api")
            config: Non-secret configuration values
            secrets: Secret values to store in keyring (key -> value)

        Returns:
            True if successful, False otherwise
        """
        data = self._read_config_file()

        if "adapters" not in data:
            data["adapters"] = {}
        if integration not in data["adapters"]:
            data["adapters"][integration] = {}

        data["adapters"][integration][adapter_type] = config

        if secrets:
            for key, value in secrets.items():
                keyring_path = f"adapters.{integration}.{adapter_type}.{key}"
                if not keyring_utils.set_secret(keyring_path, value):
                    logger.error(f"Failed to store secret: {key}")
                    return False

        if not self._write_config_file(data):
            return False

        return True

    def get_adapter_secret(self, integration: str, adapter_type: str, key: str) -> str | None:
        """Get a secret value for an adapter from keyring.

        Args:
            integration: Integration ID (e.g., "gitlab", "jira")
            adapter_type: Adapter type ("cli" or "api")
            key: Secret key name (e.g., "token")

        Returns:
            Secret value or None if not found
        """
        keyring_path = f"adapters.{integration}.{adapter_type}.{key}"
        return keyring_utils.get_secret(keyring_path)

    def is_configured(self) -> bool:
        """Check if any integration is configured.

        Returns:
            True if at least one adapter is selected and configured
        """
        for integration in ["gitlab", "jira", "todoist", "github"]:
            adapter = getattr(self._model.adapters, integration, None)
            if adapter and adapter.selected:
                return True
        legacy_configured = bool(self.gitlab_group or self.jira_project or self.todoist_token)
        return legacy_configured

    def require_gitlab_group(self) -> str:
        """Get GitLab group, raising error if not configured.

        Returns:
            GitLab group name.

        Raises:
            ConfigError: If group is not configured.
        """
        group = self.gitlab_group
        if not group:
            raise ConfigError(
                "GitLab group not configured.\n"
                "\nSet one of:\n"
                "  - Environment variable: export MONOCLI_GITLAB_GROUP='your-group'\n"
                "  - Config file: ~/.config/monocli/config.yaml\n"
                "\nConfig file format:\n"
                "  gitlab:\n"
                "    group: your-group"
            )
        return group

    def require_jira_base_url(self) -> str:
        """Get Jira base URL, raising error if not configured.

        Returns:
            Jira base URL (e.g., "https://company.atlassian.net").

        Raises:
            ConfigError: If base URL is not configured.
        """
        base_url = self.jira_base_url
        if not base_url:
            raise ConfigError(
                "Jira base URL not configured.\n"
                "\nSet one of:\n"
                "  - Environment variable: export MONOCLI_JIRA_BASE_URL='https://your-company.atlassian.net'\n"
                "  - Config file: ~/.config/monocli/config.yaml\n"
                "\nConfig file format:\n"
                "  jira:\n"
                "    base_url: https://your-company.atlassian.net"
            )
        return base_url

    def _migrate_todoist_token_to_keyring(self, token: str) -> None:
        """Migrate plaintext token to keyring and remove from config file.

        Args:
            token: Plaintext token from config file

        Raises:
            ConfigError: If keyring storage fails
        """
        try:
            if keyring_utils.set_token("todoist", token):
                logger.debug("Migrated Todoist token to keyring")

                self._remove_token_from_config_file("todoist")

                self._model.todoist.token = None
            else:
                logger.error("Failed to migrate token to keyring")
                raise ConfigError(
                    "Failed to store token in system keyring. "
                    "Ensure keyring is properly configured."
                )
        except ImportError as e:
            logger.error("Keyring not available", exc_info=e)
            raise ConfigError(
                "Keyring is required for secure token storage but is not available.\n"
                "Please ensure your system has a supported keyring backend:\n"
                "  macOS: Keychain (built-in)\n"
                "  Linux: gnome-keyring or kwallet\n"
                "  Windows: Credential Manager (built-in)"
            ) from e

    def _remove_token_from_config_file(self, service: str) -> None:
        """Remove token from config YAML file on disk.

        Args:
            service: Service name (e.g., "todoist")
        """
        # Find which config file was loaded
        config_path = None
        for path in CONFIG_PATHS:
            if path.exists():
                config_path = path
                break

        if not config_path:
            return  # No config file exists

        try:
            # Read current config
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}

            # Remove token
            if service in data and "token" in data[service]:
                del data[service]["token"]

                # Write back
                with open(config_path, "w") as f:
                    yaml.safe_dump(data, f, default_flow_style=False)

                logger.debug(f"Removed {service} token from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to remove token from config file: {e}")
            # Non-fatal - token is already in keyring


def validate_keyring_available() -> None:
    """Validate keyring is available before app starts.

    Raises:
        ConfigError: If keyring is not available and no env var is set.
    """
    # Skip validation if using environment variable (no keyring needed)
    if os.getenv("MONOCLI_TODOIST_TOKEN"):
        return

    # Check if a todoist token is configured (in config file)
    config = get_config()
    if config.todoist_token is None:
        # No token configured, no need for keyring validation
        return

    # Validate keyring is available
    if not keyring_utils.is_available():
        raise ConfigError(
            "System keyring is not available.\n\n"
            "monocli requires secure credential storage for Todoist. Please ensure:\n"
            "  macOS: Keychain is accessible (built-in)\n"
            "  Linux: Install gnome-keyring or kwallet\n"
            "  Windows: Credential Manager is accessible (built-in)\n\n"
            "If running in a headless/SSH environment, you can:\n"
            "  - Set MONOCLI_TODOIST_TOKEN environment variable\n"
            "  - Set up a keyring daemon"
        )


def get_config() -> Config:
    """Get the global configuration instance.

    Returns:
        Loaded Config instance.
    """
    return Config.load()
