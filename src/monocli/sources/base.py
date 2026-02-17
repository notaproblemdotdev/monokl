"""Base classes and protocols for data sources.

Provides Source protocols and base implementations for CLI and API-based sources.
"""

from __future__ import annotations

import typing as t
from abc import ABC
from abc import abstractmethod

if t.TYPE_CHECKING:
    from monocli.models import CodeReview
    from monocli.models import PieceOfWork


@t.runtime_checkable
class Source(t.Protocol):
    """Base protocol for all data sources.

    All sources must implement availability checking and authentication.
    """

    @property
    def source_type(self) -> str:
        """Return the source type identifier (e.g., 'gitlab', 'jira')."""
        ...

    @property
    def source_icon(self) -> str:
        """Return the source icon emoji (e.g., '🦊', '🔴')."""
        ...

    async def is_available(self) -> bool:
        """Check if the source is available (CLI installed, API accessible, etc.)."""
        ...

    async def check_auth(self) -> bool:
        """Check if the source is authenticated."""
        ...


@t.runtime_checkable
class PieceOfWorkSource(Source, t.Protocol):
    """Protocol for sources that provide work items (issues, tasks).

    Implemented by Jira, Todoist, GitHub Issues, GitLab Issues, Linear, etc.
    """

    async def fetch_items(self) -> list[PieceOfWork]:
        """Fetch work items from this source.

        Returns:
            List of PieceOfWork items.
        """
        ...


@t.runtime_checkable
class CodeReviewSource(Source, t.Protocol):
    """Protocol for sources that provide code reviews (MRs, PRs).

    Implemented by GitLab MRs, GitHub PRs, etc.
    """

    async def fetch_assigned(self) -> list[CodeReview]:
        """Fetch code reviews assigned to the current user.

        Returns:
            List of CodeReview items assigned to the user.
        """
        ...

    async def fetch_authored(self) -> list[CodeReview]:
        """Fetch code reviews authored by the current user.

        Returns:
            List of CodeReview items authored by the user.
        """
        ...

    async def fetch_pending_review(self) -> list[CodeReview]:
        """Fetch code reviews pending the current user's review.

        Returns:
            List of CodeReview items where user is a reviewer.
        """
        ...


class CLIBaseAdapter(ABC):  # noqa: B024
    """Base class for CLI-based adapters.

    Wraps CLIAdapter from async_utils to provide common functionality.
    """

    def __init__(self, cli_name: str) -> None:
        self.cli_name = cli_name
        self._available: bool | None = None

    async def is_available(self) -> bool:
        """Check if the CLI is installed."""
        import shutil

        if self._available is None:
            self._available = shutil.which(self.cli_name) is not None
        return self._available

    async def run(self, args: list[str], **kwargs) -> tuple[str, str]:
        """Run CLI with given arguments."""
        from monocli.async_utils import run_cli_command

        return await run_cli_command([self.cli_name] + args, **kwargs)

    async def fetch_json(self, args: list[str], **kwargs) -> list[dict] | dict:
        """Run CLI command and parse JSON output."""
        import json

        stdout, _stderr = await self.run(args, **kwargs)
        if not stdout.strip():
            return []
        result = json.loads(stdout)
        if isinstance(result, dict):
            return result
        return result if isinstance(result, list) else [result]


class APIBaseAdapter(ABC):
    """Base class for API-based adapters.

    Provides common functionality for REST API sources.
    """

    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the API is accessible."""
        ...

    @abstractmethod
    async def check_auth(self) -> bool:
        """Check if the API token is valid."""
        ...
