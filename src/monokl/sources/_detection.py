"""CLI detection module for discovering and validating CLI availability.

Provides mechanisms to detect if CLI tools are installed and authenticated,
with caching to avoid repeated system calls.
"""

import shutil
from typing import TypedDict

from monokl import get_logger
from monokl.async_utils import run_cli_command
from monokl.exceptions import CLIAuthError
from monokl.exceptions import CLINotFoundError

logger = get_logger(__name__)


class DetectionResult(TypedDict):
    """Result of CLI detection check.

    Attributes:
        cli_name: Name of the CLI tool (e.g., "glab", "acli")
        is_installed: Whether the CLI executable is available
        is_authenticated: Whether the CLI has valid authentication
        error_message: Error message if detection failed, None otherwise
    """

    cli_name: str
    is_installed: bool
    is_authenticated: bool
    error_message: str | None


class CLIDetector:
    """Detects if a specific CLI is installed and authenticated.

    This class checks both installation status (via shutil.which) and
    authentication status (via a lightweight trial command).

    Example:
        detector = CLIDetector("glab", ["auth", "status"])
        result = await detector.check_availability()
        # result["is_installed"] == True
        # result["is_authenticated"] == True
    """

    def __init__(self, cli_name: str, test_args: list[str]) -> None:
        """Initialize a CLI detector.

        Args:
            cli_name: Name of the CLI executable (e.g., "glab", "acli")
            test_args: Command arguments to test authentication.
                      Should be lightweight (e.g., ["auth", "status"])
                      rather than fetching actual data.
        """
        self.cli_name = cli_name
        self.test_args = test_args

    async def check_availability(self) -> DetectionResult:
        """Check if the CLI is installed and authenticated.

        First checks if the executable exists using shutil.which().
        If installed, runs the test command to validate authentication.

        Returns:
            DetectionResult with status fields populated:
            - is_installed: True if executable found
            - is_authenticated: True if test command succeeds
            - error_message: Description of what failed

        Example:
            detector = CLIDetector("glab", ["auth", "status"])
            result = await detector.check_availability()

            if result["is_installed"] and result["is_authenticated"]:
                print(f"{result['cli_name']} is ready to use")
            elif not result["is_installed"]:
                print(f"Please install {result['cli_name']}")
            else:
                print(f"Please authenticate: {result['error_message']}")
        """
        logger.debug("Checking CLI availability", cli=self.cli_name)

        # Check if CLI is installed
        if not shutil.which(self.cli_name):
            logger.warning("CLI not installed", cli=self.cli_name)
            return DetectionResult(
                cli_name=self.cli_name,
                is_installed=False,
                is_authenticated=False,
                error_message=f"{self.cli_name}: command not found",
            )

        # Check if CLI is authenticated
        try:
            await run_cli_command([self.cli_name] + self.test_args, timeout=10.0)
            logger.debug("CLI authenticated", cli=self.cli_name)
            return DetectionResult(
                cli_name=self.cli_name,
                is_installed=True,
                is_authenticated=True,
                error_message=None,
            )
        except CLIAuthError as e:
            logger.warning("CLI not authenticated", cli=self.cli_name)
            return DetectionResult(
                cli_name=self.cli_name,
                is_installed=True,
                is_authenticated=False,
                error_message=e.message,
            )
        except CLINotFoundError:
            # This shouldn't happen since we checked above, but handle it
            logger.error("CLI unexpectedly not found", cli=self.cli_name)
            return DetectionResult(
                cli_name=self.cli_name,
                is_installed=False,
                is_authenticated=False,
                error_message=f"{self.cli_name}: command not found",
            )
        except Exception as e:
            logger.error("CLI detection failed", cli=self.cli_name, error=str(e))
            return DetectionResult(
                cli_name=self.cli_name,
                is_installed=True,
                is_authenticated=False,
                error_message=str(e),
            )


class DetectionRegistry:
    """Registry for managing multiple CLI detectors.

    Provides a centralized way to register detectors for different CLIs
    and run detection checks concurrently. Results are cached after the
    first detection run to avoid repeated system calls.

    Example:
        registry = DetectionRegistry()
        registry.register(CLIDetector("glab", ["auth", "status"]))
        registry.register(CLIDetector("acli", ["me"]))

        # Run all detections concurrently
        results = await registry.detect_all()

        # Query available CLIs
        available = registry.get_available()  # ["glab"] (if authenticated)

        if registry.is_available("glab"):
            # Use glab for data fetching
            pass
    """

    def __init__(self) -> None:
        """Initialize an empty detection registry."""
        self._detectors: dict[str, CLIDetector] = {}
        self._cached_results: dict[str, DetectionResult] | None = None

    def register(self, detector: CLIDetector) -> None:
        """Register a CLI detector.

        Args:
            detector: CLIDetector instance to register

        Example:
            registry = DetectionRegistry()
            registry.register(CLIDetector("glab", ["auth", "status"]))
        """
        self._detectors[detector.cli_name] = detector
        # Invalidate cache when new detector added
        self._cached_results = None

    async def detect_all(self) -> dict[str, DetectionResult]:
        """Run detection for all registered CLIs.

        Runs all detector checks concurrently using asyncio.gather
        for efficiency. Results are cached and returned on subsequent
        calls to avoid repeated system calls.

        Returns:
            Dictionary mapping CLI names to their DetectionResults.

        Example:
            registry = DetectionRegistry()
            registry.register(CLIDetector("glab", ["auth", "status"]))

            results = await registry.detect_all()
            # results == {
            #     "glab": {
            #         "cli_name": "glab",
            #         "is_installed": True,
            #         "is_authenticated": True,
            #         "error_message": None
            #     }
            # }
        """
        # Return cached results if available
        if self._cached_results is not None:
            return self._cached_results.copy()

        import asyncio

        logger.info("Running CLI detection", cli_count=len(self._detectors))

        # Run all detectors concurrently
        coroutines = [detector.check_availability() for detector in self._detectors.values()]
        results_list: list[DetectionResult | BaseException] = await asyncio.gather(
            *coroutines, return_exceptions=True
        )

        # Build results dictionary
        results: dict[str, DetectionResult] = {}
        for cli_name, raw_result in zip(self._detectors.keys(), results_list, strict=True):
            if isinstance(raw_result, BaseException):
                # Handle any exceptions that slipped through
                results[cli_name] = DetectionResult(
                    cli_name=cli_name,
                    is_installed=False,
                    is_authenticated=False,
                    error_message=str(raw_result),
                )
            else:
                results[cli_name] = raw_result

        # Cache results
        self._cached_results = results
        logger.info("CLI detection complete", results=results)
        return results.copy()

    def get_available(self) -> list[str]:
        """Get list of CLIs that are installed and authenticated.

        Returns CLI names that have both is_installed=True and
        is_authenticated=True in their detection results.

        Note: Must call detect_all() first to populate results.

        Returns:
            List of CLI names that are available for use.

        Example:
            await registry.detect_all()
            available = registry.get_available()
            # available == ["glab"] if glab is installed and authenticated
        """
        if self._cached_results is None:
            return []

        return [
            name
            for name, result in self._cached_results.items()
            if result["is_installed"] and result["is_authenticated"]
        ]

    def is_available(self, cli_name: str) -> bool:
        """Check if a specific CLI is available.

        A CLI is considered available only if it is both installed
        AND authenticated.

        Note: Must call detect_all() first to populate results.

        Args:
            cli_name: Name of the CLI to check

        Returns:
            True if the CLI is installed and authenticated, False otherwise.

        Example:
            await registry.detect_all()
            if registry.is_available("glab"):
                # Fetch GitLab data
                pass
        """
        if self._cached_results is None:
            return False

        result = self._cached_results.get(cli_name)
        if result is None:
            return False

        return result["is_installed"] and result["is_authenticated"]

    def clear_cache(self) -> None:
        """Clear cached detection results.

        Forces the next detect_all() call to re-run all detection
        checks. Useful for testing or when CLI status may have changed.
        """
        self._cached_results = None
