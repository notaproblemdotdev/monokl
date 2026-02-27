"""Configuration management for monocle.

Reads configuration from environment variables and config files.
Priority: environment variables > keyring > config file > defaults
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from monocle import get_logger
from monocle import keyring_utils
from monocle.config_models import AppConfig

logger = get_logger(__name__)

# Default config locations (in priority order)
CONFIG_PATHS = [
    Path.home() / ".config" / "monocle" / "config.yaml",
    Path.home() / ".monocle.yaml",
    Path.cwd() / ".monocle.yaml",
]

# Default cache TTL in seconds (5 minutes)
DEFAULT_CACHE_TTL = 300

# Default cache cleanup threshold in days
DEFAULT_CACHE_CLEANUP_DAYS = 30


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


class Config:
    """Configuration manager for monocle.

    Loads configuration from environment variables and YAML config files.
    Environment variables take precedence over config file values.

    Environment variables:
        MONOCLE_GITLAB_GROUP: Default GitLab group to fetch MRs from
        MONOCLE_GITLAB_PROJECT: Alias for GitLab group/scope
        MONOCLE_JIRA_PROJECT: Default Jira project to fetch issues from
        MONOCLE_TODOIST_TOKEN: Todoist API token

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

        model = cls._validate_model(data)
        return cls(model)

    @staticmethod
    def _validate_model(data: dict[str, Any]) -> AppConfig:
        """Validate raw config data with Pydantic schema.

        Args:
            data: Raw configuration dictionary.

        Returns:
            Validated AppConfig model.

        Raises:
            ConfigError: If validation fails.
        """
        try:
            return AppConfig.from_dict(data)
        except ValidationError as e:
            messages = []
            for error in e.errors():
                location = ".".join(str(part) for part in error["loc"])
                messages.append(f"- {location}: {error['msg']}")
            details = "\n".join(messages)
            raise ConfigError(f"Invalid config format:\n{details}") from e

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
        if "features" not in data:
            data["features"] = {}

        # GitLab settings
        gitlab_group = os.getenv("MONOCLE_GITLAB_GROUP")
        if gitlab_group:
            data["gitlab"]["group"] = gitlab_group
        gitlab_project = os.getenv("MONOCLE_GITLAB_PROJECT")
        if gitlab_project and "group" not in data["gitlab"]:
            data["gitlab"]["group"] = gitlab_project

        # Jira settings
        jira_project = os.getenv("MONOCLE_JIRA_PROJECT")
        if jira_project:
            data["jira"]["project"] = jira_project
        jira_base_url = os.getenv("MONOCLE_JIRA_BASE_URL")
        if jira_base_url:
            data["jira"]["base_url"] = jira_base_url

        # Todoist settings
        todoist_token = os.getenv("MONOCLE_TODOIST_TOKEN")
        if todoist_token:
            data["todoist"]["token"] = todoist_token

        # Azure DevOps settings
        if "azuredevops" not in data:
            data["azuredevops"] = {}

        azuredevops_token = os.getenv("MONOCLE_AZUREDEVOPS_TOKEN")
        if azuredevops_token:
            data["azuredevops"]["token"] = azuredevops_token

        # Cache/Database settings from environment
        db_path = os.getenv("MONOCLE_DB_PATH")
        if db_path:
            data["cache"]["db_path"] = db_path

        cache_ttl = os.getenv("MONOCLE_CACHE_TTL")
        if cache_ttl:
            try:
                data["cache"]["ttl_seconds"] = int(cache_ttl)
            except ValueError:
                pass

        feature_experimental = os.getenv("MONOCLE_FEATURE_EXPERIMENTAL")
        if feature_experimental:
            data["features"]["experimental"] = feature_experimental.lower() in ("true", "1", "yes")

        return data

    @property
    def gitlab_group(self) -> str | None:
        """Get the configured GitLab scope/group.

        Resolution order:
        1. Top-level config: gitlab.group
        2. Adapter config: adapters.gitlab.cli.group
        3. Adapter config aliases: adapters.gitlab.cli.project / project_key
        """
        if self._model.gitlab.group:
            return self._model.gitlab.group

        adapter_cli = self.get_adapter_config("gitlab", "cli")
        for key in ("group", "project", "project_key"):
            value = adapter_cli.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

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
        1. Environment variable MONOCLE_TODOIST_TOKEN (highest priority)
        2. Environment variable TODOIST_API_TOKEN or TODOIST_TOKEN
        3. System keyring (secure storage)
        4. Config file (legacy, auto-migrates to keyring)

        Returns:
            Todoist API token or None if not configured.
        """
        env_token = os.getenv("MONOCLE_TODOIST_TOKEN")
        if env_token:
            return env_token

        legacy_env_token = os.getenv("TODOIST_API_TOKEN") or os.getenv("TODOIST_TOKEN")
        if legacy_env_token:
            return legacy_env_token

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
    def azuredevops_token(self) -> str | None:
        """Get Azure DevOps PAT token.

        Priority: env var > keyring

        Returns:
            Azure DevOps PAT token or None if not configured.
        """
        env_token = os.getenv("MONOCLE_AZUREDEVOPS_TOKEN")
        if env_token:
            return env_token

        keyring_token = keyring_utils.get_token("azuredevops")
        if keyring_token:
            return keyring_token

        return None

    @property
    def azuredevops_organizations(self) -> list[dict[str, str]]:
        """Get configured Azure DevOps orgs/projects.

        Returns:
            List of dicts with 'organization' and 'project' keys.
        """
        return [
            {"organization": org.organization, "project": org.project}
            for org in self._model.azuredevops.organizations
        ]

    @property
    def db_path(self) -> str | None:
        """Get the database path from environment or config."""
        env_path = os.getenv("MONOCLE_DB_PATH")
        if env_path:
            return env_path
        return self._model.cache.db_path

    @property
    def cache_ttl(self) -> int:
        """Get the cache TTL in seconds."""
        env_ttl = os.getenv("MONOCLE_CACHE_TTL")
        if env_ttl:
            try:
                return int(env_ttl)
            except ValueError:
                logger.warning("Invalid MONOCLE_CACHE_TTL value", value=env_ttl)
        return self._model.cache.ttl_seconds

    @property
    def offline_mode(self) -> bool:
        """Get whether offline mode is enabled."""
        return os.getenv("MONOCLE_OFFLINE_MODE", "").lower() in ("true", "1", "yes")

    @property
    def experimental_features(self) -> bool:
        """Get whether experimental features are enabled."""
        env_val = os.getenv("MONOCLE_FEATURE_EXPERIMENTAL", "").lower()
        if env_val in ("true", "1", "yes"):
            return True
        return self._model.features.experimental

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
        try:
            model = self._validate_model(data)
        except ConfigError as e:
            logger.error("Refusing to write invalid config", error=str(e))
            return False

        config_path = self._ensure_config_dir()

        try:
            temp_fd, temp_path = tempfile.mkstemp(
                dir=config_path.parent,
                prefix=".monocle-config-",
                suffix=".yaml",
            )
            try:
                with os.fdopen(temp_fd, "w") as f:
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
                os.replace(temp_path, config_path)
                self._model = model
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
        for integration in ["gitlab", "jira", "todoist", "github", "azuredevops"]:
            adapter = getattr(self._model.adapters, integration, None)
            if adapter and adapter.selected:
                return True
        legacy_configured = bool(
            self.gitlab_group or self.jira_project or self.todoist_token or self.azuredevops_token
        )
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
                "  - Environment variable: export MONOCLE_GITLAB_GROUP='your-group'\n"
                "  - Config file: ~/.config/monocle/config.yaml\n"
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
                "  - Environment variable: export MONOCLE_JIRA_BASE_URL='https://your-company.atlassian.net'\n"
                "  - Config file: ~/.config/monocle/config.yaml\n"
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
    if os.getenv("MONOCLE_TODOIST_TOKEN"):
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
            "monocle requires secure credential storage for Todoist. Please ensure:\n"
            "  macOS: Keychain is accessible (built-in)\n"
            "  Linux: Install gnome-keyring or kwallet\n"
            "  Windows: Credential Manager is accessible (built-in)\n\n"
            "If running in a headless/SSH environment, you can:\n"
            "  - Set MONOCLE_TODOIST_TOKEN environment variable\n"
            "  - Set up a keyring daemon"
        )


def get_config() -> Config:
    """Get the global configuration instance.

    Returns:
        Loaded Config instance.
    """
    return Config.load()
