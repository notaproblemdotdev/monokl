"""Tests for configuration management.

Tests for the Config class including loading from files,
environment variables, keyring integration, and error handling.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import yaml

from monokl.config import Config
from monokl.config import ConfigError
from monokl.config import get_config
from monokl.config import validate_keyring_available


class TestConfigLoad:
    """Tests for Config.load method."""

    def test_load_empty_config(self, tmp_path: Path) -> None:
        """Test loading with no config files creates empty config."""
        # Create config with no files present
        config = Config.load(tmp_path / "nonexistent.yaml")
        assert config.gitlab_group is None
        assert config.jira_project is None

    def test_load_from_explicit_path(self, tmp_path: Path) -> None:
        """Test loading from explicit config file path."""
        config_file = tmp_path / "config.yaml"
        config_data = {"gitlab": {"group": "my-group"}, "jira": {"project": "PROJ"}}
        config_file.write_text(yaml.dump(config_data))

        config = Config.load(config_file)
        assert config.gitlab_group == "my-group"
        assert config.jira_project == "PROJ"

    def test_load_from_default_locations(self, tmp_path: Path) -> None:
        """Test loading from default config file locations."""
        config_file = tmp_path / ".monokl.yaml"
        config_data = {"gitlab": {"group": "default-group"}}
        config_file.write_text(yaml.dump(config_data))

        # Temporarily override CONFIG_PATHS
        with patch("monokl.config.CONFIG_PATHS", [config_file]):
            config = Config.load()
            assert config.gitlab_group == "default-group"


class TestConfigEnvironmentVariables:
    """Tests for environment variable overrides."""

    def test_gitlab_group_from_env(self) -> None:
        """Test MONOKL_GITLAB_GROUP env var overrides config file."""
        with patch.dict(os.environ, {"MONOKL_GITLAB_GROUP": "env-group"}):
            config = Config.load()
            assert config.gitlab_group == "env-group"

    def test_gitlab_group_from_env_project_alias(self) -> None:
        """Test MONOKL_GITLAB_PROJECT env var is accepted as alias."""
        with patch.dict(os.environ, {"MONOKL_GITLAB_PROJECT": "env-project"}):
            config = Config.load()
            assert config.gitlab_group == "env-project"

    def test_jira_project_from_env(self) -> None:
        """Test MONOKL_JIRA_PROJECT env var overrides config file."""
        with patch.dict(os.environ, {"MONOKL_JIRA_PROJECT": "ENVPROJ"}):
            config = Config.load()
            assert config.jira_project == "ENVPROJ"

    def test_env_var_overrides_file(self, tmp_path: Path) -> None:
        """Test env vars take precedence over config file."""
        config_file = tmp_path / "config.yaml"
        config_data = {"gitlab": {"group": "file-group"}}
        config_file.write_text(yaml.dump(config_data))

        with patch.dict(os.environ, {"MONOKL_GITLAB_GROUP": "env-group"}):
            config = Config.load(config_file)
            assert config.gitlab_group == "env-group"

    def test_env_var_unset_uses_file_value(self, tmp_path: Path) -> None:
        """Test config file value used when env var not set."""
        config_file = tmp_path / "config.yaml"
        config_data = {"gitlab": {"group": "file-group"}}
        config_file.write_text(yaml.dump(config_data))

        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            config = Config.load(config_file)
            assert config.gitlab_group == "file-group"

    def test_gitlab_group_falls_back_to_adapter_cli_group(self, tmp_path: Path) -> None:
        """Test adapters.gitlab.cli.group is used when gitlab.group is missing."""
        config_file = tmp_path / "config.yaml"
        config_data = {"adapters": {"gitlab": {"cli": {"group": "adapter-group"}}}}
        config_file.write_text(yaml.dump(config_data))

        with patch.dict(os.environ, {}, clear=True):
            config = Config.load(config_file)
            assert config.gitlab_group == "adapter-group"

    def test_gitlab_group_accepts_adapter_project_key_alias(self, tmp_path: Path) -> None:
        """Test adapters.gitlab.cli.project_key is used as alias."""
        config_file = tmp_path / "config.yaml"
        config_data = {"adapters": {"gitlab": {"cli": {"project_key": "adapter-project"}}}}
        config_file.write_text(yaml.dump(config_data))

        with patch.dict(os.environ, {}, clear=True):
            config = Config.load(config_file)
            assert config.gitlab_group == "adapter-project"


class TestConfigRequireGitlabGroup:
    """Tests for require_gitlab_group method."""

    def test_require_gitlab_group_returns_value(self, tmp_path: Path) -> None:
        """Test require_gitlab_group returns the group when configured."""
        config_file = tmp_path / "config.yaml"
        config_data = {"gitlab": {"group": "my-group"}}
        config_file.write_text(yaml.dump(config_data))

        config = Config.load(config_file)
        assert config.require_gitlab_group() == "my-group"

    def test_require_gitlab_group_raises_when_missing(self) -> None:
        """Test require_gitlab_group raises ConfigError when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.load(Path("/nonexistent/config.yaml"))

        with pytest.raises(ConfigError) as exc_info:
            config.require_gitlab_group()

        assert "GitLab group not configured" in str(exc_info.value)
        assert "MONOKL_GITLAB_GROUP" in str(exc_info.value)
        assert "config.yaml" in str(exc_info.value)

    def test_require_gitlab_group_raises_with_empty_string(self, tmp_path: Path) -> None:
        """Test require_gitlab_group raises when group is empty string."""
        config_file = tmp_path / "config.yaml"
        config_data = {"gitlab": {"group": ""}}
        config_file.write_text(yaml.dump(config_data))

        config = Config.load(config_file)
        with pytest.raises(ConfigError):
            config.require_gitlab_group()


class TestConfigGetConfig:
    """Tests for get_config convenience function."""

    def test_get_config_returns_config_instance(self) -> None:
        """Test get_config returns a Config instance."""
        config = get_config()
        assert isinstance(config, Config)


class TestConfigFileErrors:
    """Tests for config file error handling."""

    def test_invalid_yaml_returns_empty_config(self, tmp_path: Path) -> None:
        """Test invalid YAML is handled gracefully."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        config = Config.load(config_file)
        # Should not raise, returns empty config
        assert config.gitlab_group is None

    def test_nonexistent_file_returns_empty_config(self) -> None:
        """Test nonexistent file is handled gracefully."""
        config = Config.load(Path("/definitely/does/not/exist.yaml"))
        assert config.gitlab_group is None
        assert config.jira_project is None

    def test_invalid_top_level_key_raises_config_error(self, tmp_path: Path) -> None:
        """Test unknown top-level keys are rejected by schema validation."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"unknown_section": {"x": 1}}))

        with pytest.raises(ConfigError) as exc_info:
            Config.load(config_file)

        assert "Invalid config format" in str(exc_info.value)
        assert "unknown_section" in str(exc_info.value)

    def test_invalid_selected_adapter_value_raises_config_error(self, tmp_path: Path) -> None:
        """Test adapters.<integration>.selected only accepts cli/api."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"adapters": {"gitlab": {"selected": "token"}}}))

        with pytest.raises(ConfigError) as exc_info:
            Config.load(config_file)

        assert "Invalid config format" in str(exc_info.value)
        assert "adapters.gitlab.selected" in str(exc_info.value)


class TestConfigKeyringIntegration:
    """Tests for keyring token storage integration."""

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_todoist_token_env_var_priority(self, mock_keyring: MagicMock) -> None:
        """Test environment variable takes priority over keyring and config."""
        with patch.dict(os.environ, {"MONOKL_TODOIST_TOKEN": "env-token"}):
            config = Config.load()
            assert config.todoist_token == "env-token"
            # Keyring should not be accessed
            mock_keyring.get_token.assert_not_called()

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_todoist_token_legacy_env_var_priority(self, mock_keyring: MagicMock) -> None:
        """Test standard Todoist env vars are supported."""
        with patch.dict(os.environ, {"TODOIST_API_TOKEN": "legacy-env-token"}):
            config = Config.load()
            assert config.todoist_token == "legacy-env-token"
            mock_keyring.get_token.assert_not_called()

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_todoist_token_from_keyring(self, mock_keyring: MagicMock) -> None:
        """Test keyring token used when no env var."""
        mock_keyring.get_token.return_value = "keyring-token"

        config = Config.load()
        assert config.todoist_token == "keyring-token"
        mock_keyring.get_token.assert_called_once_with("todoist")

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_todoist_token_migration_from_config(
        self, mock_keyring: MagicMock, tmp_path: Path
    ) -> None:
        """Test config file token migrated to keyring on first access."""
        mock_keyring.get_token.return_value = None
        mock_keyring.set_token.return_value = True
        mock_keyring.is_available.return_value = True

        # Create config with plaintext token
        config_file = tmp_path / "config.yaml"
        config_data = {"todoist": {"token": "config-token"}}
        config_file.write_text(yaml.dump(config_data))

        # Temporarily override CONFIG_PATHS
        with patch("monokl.config.CONFIG_PATHS", [config_file]):
            config = Config.load()
            # Access the token (triggers migration)
            token = config.todoist_token
            assert token == "config-token"

            # Verify token was stored in keyring
            mock_keyring.set_token.assert_called_once_with("todoist", "config-token")

            # Verify token was removed from in-memory model
            assert config._model.todoist.token is None

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_todoist_token_no_token_returns_none(self, mock_keyring: MagicMock) -> None:
        """Test None returned when no token anywhere."""
        mock_keyring.get_token.return_value = None

        config = Config.load()
        assert config.todoist_token is None

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_migration_keyring_failure_raises_error(
        self, mock_keyring: MagicMock, tmp_path: Path
    ) -> None:
        """Test ConfigError raised when keyring storage fails."""
        mock_keyring.get_token.return_value = None
        mock_keyring.set_token.return_value = False

        config_file = tmp_path / "config.yaml"
        config_data = {"todoist": {"token": "config-token"}}
        config_file.write_text(yaml.dump(config_data))

        with patch("monokl.config.CONFIG_PATHS", [config_file]):
            config = Config.load()
            with pytest.raises(ConfigError) as exc_info:
                _ = config.todoist_token

            assert "Failed to store token in system keyring" in str(exc_info.value)

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_migration_keyring_unavailable_raises_error(
        self, mock_keyring: MagicMock, tmp_path: Path
    ) -> None:
        """Test ConfigError raised when keyring package not available."""
        mock_keyring.get_token.return_value = None
        mock_keyring.set_token.side_effect = ImportError("keyring package is required")

        config_file = tmp_path / "config.yaml"
        config_data = {"todoist": {"token": "config-token"}}
        config_file.write_text(yaml.dump(config_data))

        with patch("monokl.config.CONFIG_PATHS", [config_file]):
            config = Config.load()
            with pytest.raises(ConfigError) as exc_info:
                _ = config.todoist_token

            assert "Keyring is required for secure token storage" in str(exc_info.value)


class TestValidateKeyringAvailable:
    """Tests for validate_keyring_available function."""

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_validation_skipped_with_env_var(self, mock_keyring: MagicMock) -> None:
        """Test validation skipped when env var is set."""
        with patch.dict(os.environ, {"MONOKL_TODOIST_TOKEN": "env-token"}):
            # Should not raise
            validate_keyring_available()
            mock_keyring.is_available.assert_not_called()

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_validation_skipped_no_token_configured(
        self, mock_keyring: MagicMock, tmp_path: Path
    ) -> None:
        """Test validation skipped when no token configured."""
        # Ensure get_token returns None (not a truthy MagicMock)
        mock_keyring.get_token.return_value = None
        # Point to non-existent config file to ensure no token configured
        with patch("monokl.config.CONFIG_PATHS", [tmp_path / "nonexistent.yaml"]):
            # Should not raise, no keyring check needed
            validate_keyring_available()
            mock_keyring.is_available.assert_not_called()

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_validation_passes_with_keyring_available(
        self, mock_keyring: MagicMock, tmp_path: Path
    ) -> None:
        """Test validation passes when keyring is available."""
        mock_keyring.is_available.return_value = True
        mock_keyring.get_token.return_value = "keyring-token"

        config_file = tmp_path / "config.yaml"
        config_data = {"todoist": {"token": "config-token"}}
        config_file.write_text(yaml.dump(config_data))

        with patch("monokl.config.CONFIG_PATHS", [config_file]):
            # Should not raise
            validate_keyring_available()
            mock_keyring.is_available.assert_called_once()

    @patch("monokl.config.keyring_utils")
    @patch.dict(os.environ, {}, clear=True)
    def test_validation_fails_without_keyring(
        self, mock_keyring: MagicMock, tmp_path: Path
    ) -> None:
        """Test validation fails when keyring is not available."""
        mock_keyring.is_available.return_value = False
        mock_keyring.get_token.return_value = "keyring-token"

        config_file = tmp_path / "config.yaml"
        config_data = {"todoist": {"token": "config-token"}}
        config_file.write_text(yaml.dump(config_data))

        with patch("monokl.config.CONFIG_PATHS", [config_file]):
            with pytest.raises(ConfigError) as exc_info:
                validate_keyring_available()

            assert "System keyring is not available" in str(exc_info.value)
            assert "monokl requires secure credential storage" in str(exc_info.value)


class TestConfigShowLogsCommand:
    """Tests for show_logs_command property."""

    def test_default_show_logs_command(self) -> None:
        """Test default command when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.load(Path("/nonexistent/config.yaml"))
            assert config.show_logs_command == "tail -f {file}"

    def test_custom_show_logs_command(self, tmp_path: Path) -> None:
        """Test custom command from config file."""
        config_file = tmp_path / "config.yaml"
        config_data = {"dev": {"show_logs_command": "less +F {file}"}}
        config_file.write_text(yaml.dump(config_data))

        config = Config.load(config_file)
        assert config.show_logs_command == "less +F {file}"

    def test_show_logs_command_with_bat(self, tmp_path: Path) -> None:
        """Test command with bat (common alternative)."""
        config_file = tmp_path / "config.yaml"
        config_data = {"dev": {"show_logs_command": "bat {file}"}}
        config_file.write_text(yaml.dump(config_data))

        config = Config.load(config_file)
        assert config.show_logs_command == "bat {file}"


class TestConfigSchemaValidationOnWrite:
    """Tests for schema validation before writing config files."""

    def test_reject_invalid_selected_adapter_without_writing(self, tmp_path: Path) -> None:
        """set_selected_adapter should reject unsupported adapter types."""
        config_path = tmp_path / "config.yaml"

        with patch("monokl.config.CONFIG_PATHS", [config_path]):
            config = Config.load()
            assert config.set_selected_adapter("gitlab", "token") is False
            assert not config_path.exists()
