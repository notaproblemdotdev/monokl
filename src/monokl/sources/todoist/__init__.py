"""Todoist source for work items.

Provides TodoistSource for fetching tasks from Todoist.
Implements PieceOfWorkSource protocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from monokl import get_logger
from monokl import keyring_utils
from monokl.config import get_config
from monokl.models import PieceOfWork
from monokl.sources.base import AdapterStatus
from monokl.sources.base import PieceOfWorkSource
from monokl.sources.base import SetupAction
from monokl.sources.base import SetupCapableSource
from monokl.sources.base import SetupParam
from monokl.sources.base import SetupResult

from ._api import TodoistAdapter

logger = get_logger(__name__)


class TodoistSource(PieceOfWorkSource, SetupCapableSource):
    """Source for Todoist tasks.

    Wraps the existing TodoistAdapter to provide PieceOfWork items.

    Example:
        source = TodoistSource(token="your-token")

        # Check if available
        if await source.is_available():
            # Fetch tasks
            items = await source.fetch_items()
            for item in items:
                print(f"{item.display_key()}: {item.title}")
    """

    def __init__(
        self,
        token: str,
        project_names: list[str] | None = None,
        show_completed: bool = False,
        show_completed_for_last: str | None = None,
    ) -> None:
        """Initialize the Todoist piece of work source.

        Args:
            token: Todoist API token
            project_names: Optional list of project names to filter by
            show_completed: Whether to include completed tasks
            show_completed_for_last: Show completed tasks from last N days
                ("24h", "48h", "72h", "7days")
        """
        self._adapter = TodoistAdapter(token)
        self.project_names = project_names
        self.show_completed = show_completed
        self.show_completed_for_last = show_completed_for_last

    @property
    def source_type(self) -> str:
        return "todoist"

    @property
    def source_icon(self) -> str:
        return "📝"

    @property
    def adapter_type(self) -> str:
        return "api"

    async def is_available(self) -> bool:
        return True

    async def check_auth(self) -> bool:
        return await self._adapter.check_auth()

    async def get_status(self) -> AdapterStatus:
        config = get_config()
        token = config.todoist_token

        if not token:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message="No API token configured",
            )

        try:
            adapter = TodoistAdapter(token)
            authenticated = await adapter.check_auth()
            return AdapterStatus(
                installed=True,
                authenticated=authenticated,
                configured=authenticated,
                error_message=None if authenticated else "Invalid token",
            )
        except Exception as e:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message=str(e),
            )

    @property
    def setup_actions(self) -> list[SetupAction]:
        return [
            SetupAction(
                id="verify",
                label="Verify Auth",
                icon="✓",
                description="Check if Todoist API token is valid",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="configure",
                label="Configure",
                icon="⚙️",
                description="Set up Todoist API token",
                requires_params=True,
                external_process=False,
                save_action=True,
                params=[
                    SetupParam(
                        id="token",
                        label="API Token",
                        type="password",
                        required=True,
                        secret=True,
                        placeholder="Enter your Todoist API token",
                        help_text="Get your token from todoist.com/prefs/integrations",
                    ),
                ],
            ),
        ]

    async def execute_setup_action(self, action_id: str, params: dict[str, str]) -> SetupResult:
        if action_id == "verify":
            status = await self.get_status()
            return SetupResult(
                success=status.authenticated,
                message="Token valid" if status.authenticated else "Invalid token",
            )

        if action_id == "configure":
            token = params.get("token", "").strip()
            if not token:
                return SetupResult(success=False, error="Token is required")

            try:
                adapter = TodoistAdapter(token)
                is_valid = await adapter.check_auth()
                if not is_valid:
                    return SetupResult(success=False, error="Invalid token")

                keyring_utils.set_secret("adapters.todoist.api.token", token)
                return SetupResult(success=True, message="Token saved successfully")
            except Exception as e:
                logger.exception("Failed to save Todoist config")
                return SetupResult(success=False, error=str(e))

        return SetupResult(success=False, error=f"Unknown action: {action_id}")

    def get_action_params(self, action_id: str) -> list[SetupParam]:
        for action in self.setup_actions:
            if action.id == action_id:
                return action.params
        return []

    def get_external_command(self, action_id: str) -> str | None:
        return None

    async def fetch_items(self) -> list[PieceOfWork]:
        """Fetch tasks from Todoist.

        Returns:
            List of PieceOfWork items from Todoist.
        """
        logger.info(
            "Fetching Todoist tasks",
            projects=self.project_names,
            show_completed=self.show_completed,
        )
        items = await self._adapter.fetch_tasks(
            project_names=self.project_names,
            show_completed=self.show_completed,
            show_completed_for_last=self.show_completed_for_last,
        )
        return items  # type: ignore[return-value]


class TodoistAPISetupSource(SetupCapableSource):
    """Setup-only source for Todoist API configuration."""

    @property
    def adapter_type(self) -> str:
        return "api"

    @property
    def source_type(self) -> str:
        return "todoist"

    @property
    def source_icon(self) -> str:
        return "📝"

    async def get_status(self) -> AdapterStatus:
        config = get_config()
        token = config.todoist_token

        if not token:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message="No API token configured",
            )

        try:
            adapter = TodoistAdapter(token)
            authenticated = await adapter.check_auth()
            return AdapterStatus(
                installed=True,
                authenticated=authenticated,
                configured=authenticated,
                error_message=None if authenticated else "Invalid token",
            )
        except Exception as e:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message=str(e),
            )

    @property
    def setup_actions(self) -> list[SetupAction]:
        return [
            SetupAction(
                id="verify",
                label="Verify Auth",
                icon="✓",
                description="Check if Todoist API token is valid",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="configure",
                label="Configure",
                icon="⚙️",
                description="Set up Todoist API token",
                requires_params=True,
                external_process=False,
                save_action=True,
                params=[
                    SetupParam(
                        id="token",
                        label="API Token",
                        type="password",
                        required=True,
                        secret=True,
                        placeholder="Enter your Todoist API token",
                        help_text="Get your token from todoist.com/prefs/integrations",
                    ),
                ],
            ),
        ]

    async def execute_setup_action(self, action_id: str, params: dict[str, str]) -> SetupResult:
        if action_id == "verify":
            status = await self.get_status()
            return SetupResult(
                success=status.authenticated,
                message="Token valid" if status.authenticated else "Invalid token",
            )

        if action_id == "configure":
            token = params.get("token", "").strip()
            if not token:
                return SetupResult(success=False, error="Token is required")

            try:
                adapter = TodoistAdapter(token)
                is_valid = await adapter.check_auth()
                if not is_valid:
                    return SetupResult(success=False, error="Invalid token")

                keyring_utils.set_secret("adapters.todoist.api.token", token)
                return SetupResult(success=True, message="Token saved successfully")
            except Exception as e:
                logger.exception("Failed to save Todoist config")
                return SetupResult(success=False, error=str(e))

        return SetupResult(success=False, error=f"Unknown action: {action_id}")

    def get_action_params(self, action_id: str) -> list[SetupParam]:
        for action in self.setup_actions:
            if action.id == action_id:
                return action.params
        return []

    def get_external_command(self, action_id: str) -> str | None:
        return None
