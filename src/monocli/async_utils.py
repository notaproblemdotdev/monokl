"""Async subprocess utilities for CLI operations with Textual Workers integration."""

import asyncio
import shutil
from typing import Any

from textual.worker import Worker, get_current_worker

from monocli.exceptions import CLIError, CLINotFoundError, raise_for_error


async def run_cli_command(
    cmd: list[str],
    timeout: float = 30.0,
    check: bool = True,
) -> str:
    """Run a CLI command asynchronously and return stdout.

    Args:
        cmd: Command and arguments as list
        timeout: Timeout in seconds
        check: If True, raise CLIError on non-zero exit

    Returns:
        Command stdout as string

    Raises:
        CLINotFoundError: If executable not found
        CLIError: If command fails and check=True
        asyncio.TimeoutError: If command times out
    """
    executable = cmd[0]
    if not shutil.which(executable):
        raise CLINotFoundError(executable)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        if proc.returncode is None:
            proc.kill()
        raise asyncio.TimeoutError(f"Command '{' '.join(cmd)}' timed out after {timeout}s")

    stdout_str = stdout.decode().strip()
    stderr_str = stderr.decode().strip()

    if check and proc.returncode != 0:
        raise_for_error(cmd, proc.returncode, stderr_str)

    return stdout_str


def fetch_with_worker(widget: Any, fetch_func: callable, *args, **kwargs) -> Worker:
    """Start a Textual Worker for fetching data with exclusive=True.

    Uses the @work(exclusive=True) pattern to prevent race conditions
    when multiple data fetching operations might overlap.

    Args:
        widget: Textual widget to bind worker to
        fetch_func: Async function to run
        *args, **kwargs: Arguments for fetch_func

    Returns:
        Worker instance

    Example:
        class DataFetcher(Widget):
            data = reactive(list)

            @work(exclusive=True)  # Prevents race conditions
            async def fetch_data(self) -> None:
                result = await run_cli_command(["glab", "mr", "list", "--json"])
                self.data = result
    """
    from textual.worker import Worker

    async def _exclusive_fetch() -> Any:
        return await fetch_func(*args, **kwargs)

    return widget.run_worker(
        _exclusive_fetch,
        exclusive=True,  # Prevents race conditions
        thread=True,  # Run in thread for CPU-bound parsing
    )


class CLIAdapter:
    """Base class for CLI adapters with common utilities."""

    def __init__(self, cli_name: str) -> None:
        self.cli_name = cli_name
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if the CLI is installed."""
        if self._available is None:
            self._available = shutil.which(self.cli_name) is not None
        return self._available

    async def run(self, args: list[str], **kwargs) -> str:
        """Run CLI with given arguments."""
        return await run_cli_command([self.cli_name] + args, **kwargs)
