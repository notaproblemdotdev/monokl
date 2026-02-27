"""Tests for CLI detection functionality."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from monokl.exceptions import CLIAuthError
from monokl.sources._detection import CLIDetector
from monokl.sources._detection import DetectionRegistry
from monokl.sources._detection import DetectionResult


class TestCLIDetector:
    """Tests for the CLIDetector class."""

    def test_detector_init(self) -> None:
        """Test proper initialization of CLIDetector."""
        detector = CLIDetector("glab", ["auth", "status"])

        assert detector.cli_name == "glab"
        assert detector.test_args == ["auth", "status"]

    @pytest.mark.asyncio
    async def test_check_availability_installed_and_authed(self) -> None:
        """Test detection when CLI is installed and authenticated."""
        detector = CLIDetector("glab", ["auth", "status"])

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch("monokl.sources._detection.run_cli_command") as mock_run:
                mock_run.return_value = ("", "✓ Logged in to gitlab.com as user")

                result = await detector.check_availability()

        assert result["cli_name"] == "glab"
        assert result["is_installed"] is True
        assert result["is_authenticated"] is True
        assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_check_availability_not_installed(self) -> None:
        """Test detection when CLI is not installed."""
        detector = CLIDetector("glab", ["auth", "status"])

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = await detector.check_availability()

        assert result["cli_name"] == "glab"
        assert result["is_installed"] is False
        assert result["is_authenticated"] is False
        assert result["error_message"] == "glab: command not found"

    @pytest.mark.asyncio
    async def test_check_availability_installed_not_authed(self) -> None:
        """Test detection when CLI is installed but not authenticated."""
        detector = CLIDetector("glab", ["auth", "status"])

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch("monokl.sources._detection.run_cli_command") as mock_run:
                mock_run.side_effect = CLIAuthError(
                    ["glab", "auth", "status"],
                    1,
                    "not logged in",
                )

                result = await detector.check_availability()

        assert result["cli_name"] == "glab"
        assert result["is_installed"] is True
        assert result["is_authenticated"] is False
        assert (
            result["error_message"] == "Authentication failed. Please run the CLI's login command."
        )

    @pytest.mark.asyncio
    async def test_check_availability_unknown_error(self) -> None:
        """Test detection when CLI fails with unknown error."""
        detector = CLIDetector("glab", ["auth", "status"])

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch("monokl.sources._detection.run_cli_command") as mock_run:
                mock_run.side_effect = Exception("Network error")

                result = await detector.check_availability()

        assert result["cli_name"] == "glab"
        assert result["is_installed"] is True
        assert result["is_authenticated"] is False
        assert result["error_message"] is not None
        assert "Network error" in result["error_message"]


class TestDetectionRegistry:
    """Tests for the DetectionRegistry class."""

    def test_registry_init(self) -> None:
        """Test registry initializes with empty state."""
        registry = DetectionRegistry()

        assert registry._detectors == {}
        assert registry._cached_results is None

    def test_register_detector(self) -> None:
        """Test registering a detector."""
        registry = DetectionRegistry()
        detector = CLIDetector("glab", ["auth", "status"])

        registry.register(detector)

        assert "glab" in registry._detectors
        assert registry._detectors["glab"] is detector

    def test_register_multiple_detectors(self) -> None:
        """Test registering multiple detectors."""
        registry = DetectionRegistry()
        glab_detector = CLIDetector("glab", ["auth", "status"])
        acli_detector = CLIDetector("acli", ["me"])

        registry.register(glab_detector)
        registry.register(acli_detector)

        assert "glab" in registry._detectors
        assert "acli" in registry._detectors
        assert registry._detectors["glab"] is glab_detector
        assert registry._detectors["acli"] is acli_detector

    def test_register_invalidate_cache(self) -> None:
        """Test that registering a new detector invalidates cache."""
        registry = DetectionRegistry()
        glab_detector = CLIDetector("glab", ["auth", "status"])

        registry.register(glab_detector)
        # Simulate cached results
        registry._cached_results = {"glab": MagicMock()}

        # Register new detector should clear cache
        acli_detector = CLIDetector("acli", ["me"])
        registry.register(acli_detector)

        assert registry._cached_results is None

    @pytest.mark.asyncio
    async def test_detect_all_concurrent(self) -> None:
        """Test that detect_all runs detectors concurrently."""
        registry = DetectionRegistry()

        # Create mock detectors
        glab_mock = MagicMock(spec=CLIDetector)
        glab_mock.cli_name = "glab"
        glab_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="glab",
                is_installed=True,
                is_authenticated=True,
                error_message=None,
            )
        )

        acli_mock = MagicMock(spec=CLIDetector)
        acli_mock.cli_name = "acli"
        acli_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="acli",
                is_installed=True,
                is_authenticated=False,
                error_message="Not authenticated",
            )
        )

        registry.register(glab_mock)
        registry.register(acli_mock)

        results = await registry.detect_all()

        # Verify both detectors were called
        glab_mock.check_availability.assert_called_once()
        acli_mock.check_availability.assert_called_once()

        # Verify results
        assert "glab" in results
        assert "acli" in results
        assert results["glab"]["is_installed"] is True
        assert results["glab"]["is_authenticated"] is True
        assert results["acli"]["is_installed"] is True
        assert results["acli"]["is_authenticated"] is False

    @pytest.mark.asyncio
    async def test_detect_all_caching(self) -> None:
        """Test that detect_all caches results."""
        registry = DetectionRegistry()

        detector_mock = MagicMock(spec=CLIDetector)
        detector_mock.cli_name = "glab"
        detector_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="glab",
                is_installed=True,
                is_authenticated=True,
                error_message=None,
            )
        )

        registry.register(detector_mock)

        # First call should run detection
        results1 = await registry.detect_all()
        assert detector_mock.check_availability.call_count == 1

        # Second call should return cached results
        results2 = await registry.detect_all()
        assert detector_mock.check_availability.call_count == 1  # Not called again

        # Results should be the same
        assert results1 == results2

    @pytest.mark.asyncio
    async def test_detect_all_returns_copy(self) -> None:
        """Test that detect_all returns a copy of results."""
        registry = DetectionRegistry()

        detector_mock = MagicMock(spec=CLIDetector)
        detector_mock.cli_name = "glab"
        detector_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="glab",
                is_installed=True,
                is_authenticated=True,
                error_message=None,
            )
        )

        registry.register(detector_mock)

        results1 = await registry.detect_all()
        results2 = await registry.detect_all()

        # Should be equal but not the same object
        assert results1 == results2
        assert results1 is not results2

    @pytest.mark.asyncio
    async def test_get_available(self) -> None:
        """Test getting list of available CLIs."""
        registry = DetectionRegistry()

        # Create mock detectors
        glab_mock = MagicMock(spec=CLIDetector)
        glab_mock.cli_name = "glab"
        glab_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="glab",
                is_installed=True,
                is_authenticated=True,
                error_message=None,
            )
        )

        acli_mock = MagicMock(spec=CLIDetector)
        acli_mock.cli_name = "acli"
        acli_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="acli",
                is_installed=True,
                is_authenticated=False,
                error_message="Not authenticated",
            )
        )

        gh_mock = MagicMock(spec=CLIDetector)
        gh_mock.cli_name = "gh"
        gh_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="gh",
                is_installed=False,
                is_authenticated=False,
                error_message="Not found",
            )
        )

        registry.register(glab_mock)
        registry.register(acli_mock)
        registry.register(gh_mock)

        await registry.detect_all()
        available = registry.get_available()

        # Only glab should be available (installed AND authenticated)
        assert available == ["glab"]

    def test_get_available_before_detect(self) -> None:
        """Test get_available returns empty list before detect_all called."""
        registry = DetectionRegistry()
        detector = CLIDetector("glab", ["auth", "status"])
        registry.register(detector)

        available = registry.get_available()
        assert available == []

    @pytest.mark.asyncio
    async def test_is_available_true(self) -> None:
        """Test is_available returns True for available CLI."""
        registry = DetectionRegistry()

        detector_mock = MagicMock(spec=CLIDetector)
        detector_mock.cli_name = "glab"
        detector_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="glab",
                is_installed=True,
                is_authenticated=True,
                error_message=None,
            )
        )

        registry.register(detector_mock)
        await registry.detect_all()

        assert registry.is_available("glab") is True

    @pytest.mark.asyncio
    async def test_is_available_not_authenticated(self) -> None:
        """Test is_available returns False for unauthenticated CLI."""
        registry = DetectionRegistry()

        detector_mock = MagicMock(spec=CLIDetector)
        detector_mock.cli_name = "glab"
        detector_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="glab",
                is_installed=True,
                is_authenticated=False,
                error_message="Not authenticated",
            )
        )

        registry.register(detector_mock)
        await registry.detect_all()

        assert registry.is_available("glab") is False

    @pytest.mark.asyncio
    async def test_is_available_not_installed(self) -> None:
        """Test is_available returns False for uninstalled CLI."""
        registry = DetectionRegistry()

        detector_mock = MagicMock(spec=CLIDetector)
        detector_mock.cli_name = "glab"
        detector_mock.check_availability = AsyncMock(
            return_value=DetectionResult(
                cli_name="glab",
                is_installed=False,
                is_authenticated=False,
                error_message="Not found",
            )
        )

        registry.register(detector_mock)
        await registry.detect_all()

        assert registry.is_available("glab") is False

    def test_is_available_before_detect(self) -> None:
        """Test is_available returns False before detect_all called."""
        registry = DetectionRegistry()
        detector = CLIDetector("glab", ["auth", "status"])
        registry.register(detector)

        assert registry.is_available("glab") is False

    def test_is_available_unknown_cli(self) -> None:
        """Test is_available returns False for unknown CLI."""
        registry = DetectionRegistry()
        detector = CLIDetector("glab", ["auth", "status"])
        registry.register(detector)
        # Note: not calling detect_all, so _cached_results is None

        assert registry.is_available("unknown") is False

    def test_clear_cache(self) -> None:
        """Test that clear_cache removes cached results."""
        registry = DetectionRegistry()

        # Simulate cached results
        registry._cached_results = {
            "glab": DetectionResult(
                cli_name="glab",
                is_installed=True,
                is_authenticated=True,
                error_message=None,
            )
        }

        registry.clear_cache()

        assert registry._cached_results is None

    @pytest.mark.asyncio
    async def test_detect_all_handles_base_exceptions(self) -> None:
        """Test that detect_all handles BaseExceptions from asyncio.gather."""
        registry = DetectionRegistry()

        # Create mock detector that raises BaseException
        detector_mock = MagicMock(spec=CLIDetector)
        detector_mock.cli_name = "glab"
        detector_mock.check_availability = AsyncMock(side_effect=BaseException("Critical error"))

        registry.register(detector_mock)

        results = await registry.detect_all()

        assert results["glab"]["is_installed"] is False
        assert results["glab"]["is_authenticated"] is False
        assert results["glab"]["error_message"] is not None
        assert "Critical error" in results["glab"]["error_message"]
