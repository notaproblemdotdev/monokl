"""Jira source for work items.

Provides JiraSource for fetching work items from Jira.
Implements PieceOfWorkSource protocol.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from monokl import get_logger
from monokl.config import get_config
from monokl.models import PieceOfWork
from monokl.sources.base import AdapterStatus
from monokl.sources.base import PieceOfWorkSource
from monokl.sources.base import SetupAction
from monokl.sources.base import SetupCapableSource
from monokl.sources.base import SetupParam
from monokl.sources.base import SetupResult

from ._cli import JiraAdapter

logger = get_logger(__name__)


class JiraSource(PieceOfWorkSource, SetupCapableSource):
    """Source for Jira work items.

    Wraps the existing JiraAdapter to provide PieceOfWork items.

    Example:
        source = JiraSource(base_url="https://company.atlassian.net")

        # Check if available
        if await source.is_available():
            # Fetch assigned work items
            items = await source.fetch_items()
            for item in items:
                print(f"{item.display_key()}: {item.title}")
    """

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize the Jira piece of work source.

        Args:
            base_url: Optional Jira base URL (e.g., "https://company.atlassian.net")
        """
        self._adapter = JiraAdapter(base_url)

    @property
    def source_type(self) -> str:
        return "jira"

    @property
    def source_icon(self) -> str:
        return "🔴"

    @property
    def adapter_type(self) -> str:
        return "cli"

    async def is_available(self) -> bool:
        return self._adapter.is_available()

    async def check_auth(self) -> bool:
        return await self._adapter.check_auth()

    async def get_status(self) -> AdapterStatus:
        installed = shutil.which("acli") is not None
        authenticated = False
        error_message = None

        if installed:
            try:
                authenticated = await self._adapter.check_auth()
                if not authenticated:
                    error_message = "Not authenticated"
            except Exception as e:
                error_message = str(e)
        else:
            error_message = "acli CLI not installed"

        return AdapterStatus(
            installed=installed,
            authenticated=authenticated,
            configured=authenticated,
            error_message=error_message,
        )

    @property
    def setup_actions(self) -> list[SetupAction]:
        return [
            SetupAction(
                id="verify",
                label="Verify Auth",
                icon="✓",
                description="Check if acli CLI is authenticated",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="login",
                label="Sign In",
                icon="🔑",
                description="Sign in to acli CLI interactively",
                requires_params=False,
                external_process=True,
                external_command="acli jira auth login",
            ),
        ]

    async def execute_setup_action(self, action_id: str, params: dict[str, str]) -> SetupResult:
        if action_id == "verify":
            status = await self.get_status()
            return SetupResult(
                success=status.authenticated,
                message="Authenticated" if status.authenticated else "Not authenticated",
            )

        return SetupResult(
            success=False,
            error=f"Unknown action: {action_id}",
        )

    def get_action_params(self, action_id: str) -> list[SetupParam]:
        return []

    def get_external_command(self, action_id: str) -> str | None:
        for action in self.setup_actions:
            if action.id == action_id and action.external_process:
                return action.external_command
        return None

    async def fetch_items(self) -> list[PieceOfWork]:
        """Fetch work items from Jira.

        Returns:
            List of PieceOfWork items from Jira.
        """
        logger.info("Fetching Jira work items")
        items = await self._adapter.fetch_assigned_items()
        return items  # type: ignore[return-value]


class JiraCLISetupSource(SetupCapableSource):
    """Setup-only source for Jira CLI configuration."""

    @property
    def adapter_type(self) -> str:
        return "cli"

    @property
    def source_type(self) -> str:
        return "jira"

    @property
    def source_icon(self) -> str:
        return "🔴"

    async def get_status(self) -> AdapterStatus:
        installed = shutil.which("acli") is not None
        authenticated = False
        error_message = None

        if installed:
            try:
                config = get_config()
                base_url = config.jira_base_url or "https://example.atlassian.net"
                adapter = JiraAdapter(base_url)
                authenticated = await adapter.check_auth()
                if not authenticated:
                    error_message = "Not authenticated"
            except Exception as e:
                error_message = str(e)
        else:
            error_message = "acli CLI not installed"

        return AdapterStatus(
            installed=installed,
            authenticated=authenticated,
            configured=authenticated,
            error_message=error_message,
        )

    @property
    def setup_actions(self) -> list[SetupAction]:
        return [
            SetupAction(
                id="verify",
                label="Verify Auth",
                icon="✓",
                description="Check if acli CLI is authenticated",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="login",
                label="Sign In",
                icon="🔑",
                description="Sign in to acli CLI interactively",
                requires_params=False,
                external_process=True,
                external_command="acli jira auth login",
            ),
        ]

    async def execute_setup_action(self, action_id: str, params: dict[str, str]) -> SetupResult:
        if action_id == "verify":
            status = await self.get_status()
            return SetupResult(
                success=status.authenticated,
                message="Authenticated" if status.authenticated else "Not authenticated",
            )

        return SetupResult(
            success=False,
            error=f"Unknown action: {action_id}",
        )

    def get_action_params(self, action_id: str) -> list[SetupParam]:
        return []

    def get_external_command(self, action_id: str) -> str | None:
        for action in self.setup_actions:
            if action.id == action_id and action.external_process:
                return action.external_command
        return None
