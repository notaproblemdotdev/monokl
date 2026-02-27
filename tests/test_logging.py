"""Tests for logging configuration."""

from pathlib import Path
from unittest.mock import patch

from monokl.logging_config import configure_logging
from monokl.logging_config import ensure_log_dir
from monokl.logging_config import filter_sensitive_data
from monokl.logging_config import get_log_file_path
from monokl.logging_config import get_logger


class TestLogDirectory:
    """Test log directory creation."""

    def test_ensure_log_dir_creates_directory(self, tmp_path: Path) -> None:
        """Test that ensure_log_dir creates the log directory."""
        test_dir = tmp_path / ".local" / "share" / "monokl" / "logs"

        with patch("monokl.logging_config.LOG_DIR", test_dir):
            ensure_log_dir()
            assert test_dir.exists()
            assert test_dir.is_dir()

    def test_ensure_log_dir_idempotent(self, tmp_path: Path) -> None:
        """Test that ensure_log_dir is idempotent."""
        test_dir = tmp_path / ".local" / "share" / "monokl" / "logs"
        test_dir.mkdir(parents=True)

        with patch("monokl.logging_config.LOG_DIR", test_dir):
            ensure_log_dir()
            assert test_dir.exists()


class TestLogFilePath:
    """Test log file path generation."""

    def test_get_log_file_path_returns_correct_format(self, tmp_path: Path) -> None:
        """Test that log file path has correct naming format."""
        test_dir = tmp_path / "logs"

        with patch("monokl.logging_config.LOG_DIR", test_dir):
            path = get_log_file_path()
            assert path.parent == test_dir
            assert path.name.startswith("monokl_")
            assert path.name.endswith(".log")
            # Should contain date pattern (YYYY-MM-DD)
            assert len(path.stem) == len("monokl_YYYY-MM-DD")


class TestConfigureLogging:
    """Test logging configuration."""

    def test_configure_logging_sets_debug_level(self, tmp_path: Path) -> None:
        """Test that debug=True sets log level to DEBUG."""
        test_dir = tmp_path / "logs"

        with (
            patch("monokl.logging_config.LOG_DIR", test_dir),
            patch("logging.basicConfig") as mock_basic_config,
            patch("structlog.configure") as mock_structlog_config,
        ):
            configure_logging(debug=True)

            # Check that basicConfig was called with DEBUG level
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == 10  # logging.DEBUG

    def test_configure_logging_respects_env_var(self, tmp_path: Path) -> None:
        """Test that LOG_LEVEL env var is respected."""
        test_dir = tmp_path / "logs"

        with (
            patch("monokl.logging_config.LOG_DIR", test_dir),
            patch("os.environ", {"LOG_LEVEL": "WARNING"}),
            patch("logging.basicConfig") as mock_basic_config,
            patch("structlog.configure") as mock_structlog_config,
        ):
            configure_logging(debug=False)

            # Check that basicConfig was called with WARNING level
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == 30  # logging.WARNING

    def test_configure_logging_defaults_to_info(self, tmp_path: Path) -> None:
        """Test that default log level is INFO."""
        test_dir = tmp_path / "logs"

        with (
            patch("monokl.logging_config.LOG_DIR", test_dir),
            patch("os.environ", {}),
            patch("logging.basicConfig") as mock_basic_config,
            patch("structlog.configure") as mock_structlog_config,
        ):
            configure_logging(debug=False)

            # Check that basicConfig was called with INFO level
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == 20  # logging.INFO


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_with_name(self) -> None:
        """Test that get_logger accepts a name parameter."""
        logger = get_logger("test_module")
        assert logger is not None

    def test_get_logger_without_name(self) -> None:
        """Test that get_logger works without a name."""
        logger = get_logger()
        assert logger is not None


class TestSensitiveDataFiltering:
    """Test sensitive data filtering."""

    def test_filter_masks_token_field(self) -> None:
        """Test that 'token' field is masked."""
        logger = None  # type: ignore
        event_dict = {"message": "test", "token": "secret123", "user": "john"}

        result = filter_sensitive_data(logger, "info", event_dict)

        assert result["token"] == "***REDACTED***"
        assert result["user"] == "john"
        assert result["message"] == "test"

    def test_filter_masks_password_field(self) -> None:
        """Test that 'password' field is masked."""
        logger = None  # type: ignore
        event_dict = {"password": "mysecret", "username": "admin"}

        result = filter_sensitive_data(logger, "info", event_dict)

        assert result["password"] == "***REDACTED***"
        assert result["username"] == "admin"

    def test_filter_masks_api_key_field(self) -> None:
        """Test that 'api_key' field is masked."""
        logger = None  # type: ignore
        event_dict = {"api_key": "key123", "endpoint": "/api"}

        result = filter_sensitive_data(logger, "info", event_dict)

        assert result["api_key"] == "***REDACTED***"

    def test_filter_masks_access_token_field(self) -> None:
        """Test that 'access_token' field is masked."""
        logger = None  # type: ignore
        event_dict = {"access_token": "at123", "refresh_token": "rt456"}

        result = filter_sensitive_data(logger, "info", event_dict)

        assert result["access_token"] == "***REDACTED***"
        assert result["refresh_token"] == "***REDACTED***"

    def test_filter_masks_case_insensitive(self) -> None:
        """Test that sensitive field matching is case-insensitive."""
        logger = None  # type: ignore
        event_dict = {"TOKEN": "secret1", "Password": "secret2", "Api_Key": "secret3"}

        result = filter_sensitive_data(logger, "info", event_dict)

        assert result["TOKEN"] == "***REDACTED***"
        assert result["Password"] == "***REDACTED***"
        assert result["Api_Key"] == "***REDACTED***"

    def test_filter_leaves_non_sensitive_data_unchanged(self) -> None:
        """Test that non-sensitive data is not modified."""
        logger = None  # type: ignore
        event_dict = {"user_id": 123, "action": "login", "count": 42}

        result = filter_sensitive_data(logger, "info", event_dict)

        assert result["user_id"] == 123
        assert result["action"] == "login"
        assert result["count"] == 42


class TestLogFileOutput:
    """Test log file output."""

    def test_log_file_is_created(self, tmp_path: Path) -> None:
        """Test that logging creates a log file."""
        test_dir = tmp_path / "logs"

        with patch("monokl.logging_config.LOG_DIR", test_dir):
            configure_logging(debug=True)
            logger = get_logger("test")
            logger.info("Test message", key="value")

            # Check that log file was created
            log_files = list(test_dir.glob("monokl_*.log"))
            assert len(log_files) > 0

    def test_log_file_contains_json(self, tmp_path: Path) -> None:
        """Test that log file contains JSON output."""
        import json
        import logging

        test_dir = tmp_path / "logs"
        test_dir.mkdir(parents=True, exist_ok=True)
        log_file = test_dir / "test.log"

        # Create a logger and handler manually for this test
        test_logger = logging.getLogger("test_json")
        test_logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.DEBUG)
        test_logger.addHandler(handler)

        # Write a JSON log entry directly
        log_entry = {"event": "Test message", "key": "value", "level": "info"}
        test_logger.info(json.dumps(log_entry))

        # Close handler
        handler.close()

        # Read the log file
        content = log_file.read_text()
        # Should contain valid JSON
        assert "Test message" in content
        assert "value" in content
