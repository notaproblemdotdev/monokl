"""Custom exceptions for monocli CLI operations."""


class CLIError(Exception):
    """Base exception for CLI command failures."""

    def __init__(self, command: list[str], returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        cmd_str = " ".join(command)
        super().__init__(f"Command '{cmd_str}' failed with exit code {returncode}: {stderr[:200]}")


class CLIAuthError(CLIError):
    """Raised when CLI command fails due to authentication issues."""

    AUTH_PATTERNS = [
        "authentication failed",
        "unauthorized",
        "401",
        "not logged in",
        "not authenticated",
    ]

    def __init__(self, command: list[str], returncode: int, stderr: str) -> None:
        super().__init__(command, returncode, stderr)
        self.message = "Authentication failed. Please run the CLI's login command."


class CLINotFoundError(CLIError):
    """Raised when the CLI executable is not found."""

    def __init__(self, cli_name: str) -> None:
        self.cli_name = cli_name
        super().__init__(
            command=[cli_name], returncode=127, stderr=f"{cli_name}: command not found"
        )


def raise_for_error(command: list[str], returncode: int, stderr: str) -> None:
    """Raise appropriate exception based on error type."""
    stderr_lower = stderr.lower()
    if any(pattern in stderr_lower for pattern in CLIAuthError.AUTH_PATTERNS):
        raise CLIAuthError(command, returncode, stderr)
    raise CLIError(command, returncode, stderr)
