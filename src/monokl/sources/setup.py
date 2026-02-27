"""Setup capabilities for CLI-based adapters.

Provides base implementations for the SetupCapableSource protocol
specifically for CLI-based sources.
"""

from __future__ import annotations

import shutil

from monokl import get_logger
from monokl.sources.base import AdapterStatus
from monokl.sources.base import SetupAction
from monokl.sources.base import SetupParam
from monokl.sources.base import SetupResult

logger = get_logger(__name__)


class CLISetupMixin:
    """Mixin providing setup capabilities for CLI-based adapters.

    Usage:
        class GitLabSource(CLISetupMixin, CodeReviewSource):
            cli_name = "glab"
            source_type = "gitlab"
            source_icon = "🦊"
    """

    cli_name: str = ""
    source_type: str = ""
    source_icon: str = ""

    @property
    def adapter_type(self) -> str:
        return "cli"

    async def get_status(self) -> AdapterStatus:
        installed = shutil.which(self.cli_name) is not None
        authenticated = False
        error_message = None

        if installed:
            try:
                if hasattr(self, "check_auth"):
                    authenticated = await self.check_auth()
                if not authenticated:
                    error_message = "Not authenticated"
            except Exception as e:
                error_message = str(e)
        else:
            error_message = f"{self.cli_name} CLI not installed"

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
                description="Check if the CLI is authenticated",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="login",
                label="Sign In",
                icon="🔑",
                description=f"Sign in to {self.cli_name} CLI interactively",
                requires_params=False,
                external_process=True,
                external_command=f"{self.cli_name} auth login",
                confirm_message="This will open an interactive login session.",
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
