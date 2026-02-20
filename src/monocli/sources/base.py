"""Base classes and protocols for data sources.

Provides Source protocols and base implementations for CLI and API-based sources.
"""

from __future__ import annotations

import typing as t
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field

if t.TYPE_CHECKING:
    from monocli.models import CodeReview
    from monocli.models import PieceOfWork


@dataclass(frozen=True, slots=True)
class SetupParam:
    """Parameter definition for a setup action.

    Defines what input is required from the user for a setup action.
    """

    id: str
    label: str
    type: t.Literal["text", "password", "url"] = "text"
    required: bool = True
    default: str | None = None
    secret: bool = False
    placeholder: str | None = None
    help_text: str | None = None


@dataclass(frozen=True, slots=True)
class SetupAction:
    """Definition of a setup action available for an adapter.

    Actions can be:
    - Form-based (requires_params=True): Shows a form dialog in the UI
    - External process (external_process=True): Suspends UI and runs CLI command
    - Simple (neither): Can execute directly without user input
    - Save action (save_action=True): Saves config, shows "Save" button instead of "Execute"
    """

    id: str
    label: str
    icon: str = "⚙️"
    description: str | None = None
    requires_params: bool = False
    external_process: bool = False
    external_command: str | None = None
    confirm_message: str | None = None
    params: list[SetupParam] = field(default_factory=list)
    save_action: bool = False


@dataclass(frozen=True, slots=True)
class SetupResult:
    """Result of executing a setup action."""

    success: bool
    message: str | None = None
    error: str | None = None
    next_action: str | None = None


@dataclass(frozen=True, slots=True)
class AdapterStatus:
    """Current status of an adapter."""

    installed: bool
    authenticated: bool
    configured: bool
    error_message: str | None = None
    details: dict[str, t.Any] = field(default_factory=dict)


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


@t.runtime_checkable
class SetupCapableSource(t.Protocol):
    """Protocol for sources that support interactive setup.

    Provides methods for:
    - Checking adapter status (installed, authenticated, configured)
    - Getting available setup actions
    - Executing setup actions
    - Getting parameter definitions for form-based actions
    """

    @property
    def adapter_type(self) -> t.Literal["cli", "api"]:
        """Return the adapter type identifier."""
        ...

    @property
    def source_type(self) -> str:
        """Return the source type identifier (e.g., 'gitlab', 'jira')."""
        ...

    @property
    def source_icon(self) -> str:
        """Return the source icon emoji (e.g., '🦊', '🔴')."""
        ...

    async def get_status(self) -> AdapterStatus:
        """Get current adapter status.

        Returns:
            AdapterStatus with installation, auth, and configuration state.
        """
        ...

    @property
    def setup_actions(self) -> list[SetupAction]:
        """Return list of available setup actions.

        Returns:
            List of SetupAction definitions this source supports.
        """
        ...

    async def execute_setup_action(self, action_id: str, params: dict[str, str]) -> SetupResult:
        """Execute a setup action.

        Args:
            action_id: ID of the action to execute
            params: Parameters provided by user (for form-based actions)

        Returns:
            SetupResult indicating success/failure
        """
        ...

    def get_action_params(self, action_id: str) -> list[SetupParam]:
        """Get parameters required for a setup action.

        Args:
            action_id: ID of the action

        Returns:
            List of SetupParam definitions, or empty list if no params needed.
        """
        ...

    def get_external_command(self, action_id: str) -> str | None:
        """Get CLI command for external process actions.

        Args:
            action_id: ID of the action

        Returns:
            Command string to execute, or None if not an external action.
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
