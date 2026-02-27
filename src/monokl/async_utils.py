"""Async subprocess utilities for CLI operations with Textual Workers integration."""

import asyncio
import json
import shutil
import typing as t
from collections.abc import Callable

from pydantic import BaseModel
from textual.worker import Worker

from monokl.exceptions import CLINotFoundError
from monokl.exceptions import raise_for_error

T = t.TypeVar("T", bound=BaseModel)

# Semaphore to prevent race conditions in concurrent subprocess execution
# Limit to 3 concurrent subprocesses to avoid transport cleanup issues
_subprocess_semaphore = asyncio.Semaphore(3)


async def _cleanup_process(proc: asyncio.subprocess.Process) -> None:
    """Clean up a subprocess without triggering race conditions.

    This function handles the tricky asyncio subprocess cleanup to avoid
    InvalidStateError race conditions. It gives asyncio's internal callbacks
    time to run before attempting manual cleanup.
    """
    if proc.returncode is not None:
        return  # Already terminated

    try:
        proc.kill()
        # Use a short wait with shield to prevent cancellation issues
        # but catch InvalidStateError which can occur due to race conditions
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.0)
        except (TimeoutError, ProcessLookupError):
            pass
    except asyncio.InvalidStateError:
        # Process is in an invalid state, likely already being cleaned up
        # by asyncio's internal mechanisms - this is safe to ignore
        pass


async def run_cli_command(
    cmd: list[str],
    timeout: float = 30.0,
    check: bool = True,
) -> tuple[str, str]:
    """Run a CLI command asynchronously and return (stdout, stderr).

    Args:
        cmd: Command and arguments as list
        timeout: Timeout in seconds
        check: If True, raise CLIError on non-zero exit

    Returns:
        Tuple of (stdout, stderr) as strings

    Raises:
        CLINotFoundError: If executable not found
        CLIError: If command fails and check=True
        asyncio.TimeoutError: If command times out
    """
    executable = cmd[0]
    if not shutil.which(executable):
        raise CLINotFoundError(executable)

    async with _subprocess_semaphore:  # Prevent race conditions
        proc: asyncio.subprocess.Process | None = None
        stdout = b""
        stderr = b""

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,  # Prevent hanging on input
            )

            # Wait for completion with timeout
            # Note: use wait_for directly on communicate() instead of wrapping
            # in create_task — the extra task layer causes InvalidStateError
            # race conditions in asyncio's subprocess transport cleanup,
            # especially under Textual's event loop.
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except TimeoutError:
                # Clean up the process
                if proc.returncode is None:
                    await _cleanup_process(proc)

                raise TimeoutError(f"Command '{' '.join(cmd)}' timed out after {timeout}s")

        finally:
            # Ensure any remaining cleanup happens
            if proc is not None and proc.returncode is None:
                await _cleanup_process(proc)

        stdout_str = stdout.decode().strip()
        stderr_str = stderr.decode().strip()

        if check and proc is not None:
            returncode = proc.returncode
            if returncode not in (None, 0):
                raise_for_error(cmd, returncode, stderr_str)

        return stdout_str, stderr_str


def fetch_with_worker(
    widget: t.Any, fetch_func: Callable[..., t.Any], *args: t.Any, **kwargs: t.Any
) -> Worker:
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
                stdout, stderr = await run_cli_command(["glab", "mr", "list", "--json"])
                self.data = stdout
    """

    async def _exclusive_fetch() -> t.Any:
        return await fetch_func(*args, **kwargs)

    return t.cast(
        "Worker[t.Any]",
        widget.run_worker(
            _exclusive_fetch,
            exclusive=True,  # Prevents race conditions
            thread=True,  # Run in thread for CPU-bound parsing
        ),
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

    async def run(self, args: list[str], **kwargs: t.Any) -> tuple[str, str]:
        """Run CLI with given arguments.

        Returns:
            Tuple of (stdout, stderr) as strings
        """
        return await run_cli_command([self.cli_name] + args, **kwargs)

    async def fetch_json(self, args: list[str], **kwargs: t.Any) -> t.Any:
        """Run CLI command and parse JSON output from stdout.

        Args:
            args: CLI arguments
            **kwargs: Additional arguments for run_cli_command

        Returns:
            Parsed JSON as list of dicts
        """
        stdout, _stderr = await self.run(args, **kwargs)
        if not stdout.strip():
            return []
        return json.loads(stdout)

    async def fetch_and_parse(
        self, args: list[str], model_class: type[T], **kwargs: t.Any
    ) -> list[T]:
        """Run CLI command, parse JSON, and validate into Pydantic models.

        Args:
            args: CLI arguments
            model_class: Pydantic model class to parse items into
            **kwargs: Additional arguments for run_cli_command

        Returns:
            List of validated Pydantic model instances
        """
        data = await self.fetch_json(args, **kwargs)
        if not isinstance(data, list):
            data = [data]
        return [model_class.model_validate(item) for item in data]
