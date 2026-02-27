"""GitLab source for code reviews.

Provides GitLabSource for fetching merge requests from GitLab.
Implements CodeReviewSource protocol.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from monokl import get_logger
from monokl.config import get_config
from monokl.models import CodeReview
from monokl.models import MergeRequest
from monokl.sources.base import AdapterStatus
from monokl.sources.base import CodeReviewSource
from monokl.sources.base import SetupAction
from monokl.sources.base import SetupCapableSource
from monokl.sources.base import SetupParam
from monokl.sources.base import SetupResult

from ._cli import GitLabAdapter

logger = get_logger(__name__)


class GitLabSource(CodeReviewSource, SetupCapableSource):
    """Source for GitLab merge requests (code reviews).

    Wraps the existing GitLabAdapter to provide CodeReview items.

    Example:
        source = GitLabSource(group="my-group")

        # Check if available
        if await source.is_available():
            # Fetch assigned MRs
            mrs = await source.fetch_assigned()
            for mr in mrs:
                print(f"{mr.display_key()}: {mr.title}")
    """

    def __init__(self, group: str | None = None) -> None:
        """Initialize the GitLab code review source.

        Args:
            group: Optional GitLab group to search (e.g., "my-group")
        """
        self.group = group
        self._adapter = GitLabAdapter()

    @property
    def source_type(self) -> str:
        return "gitlab"

    @property
    def source_icon(self) -> str:
        return "🦊"

    @property
    def adapter_type(self) -> str:
        return "cli"

    async def is_available(self) -> bool:
        return self._adapter.is_available()

    async def check_auth(self) -> bool:
        return await self._adapter.check_auth()

    async def get_status(self) -> AdapterStatus:
        installed = shutil.which("glab") is not None
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
            error_message = "glab CLI not installed"

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
                description="Check if glab CLI is authenticated",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="login",
                label="Sign In",
                icon="🔑",
                description="Sign in to glab CLI interactively",
                requires_params=False,
                external_process=True,
                external_command="glab auth login",
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

    def _convert_mr_to_code_review(self, mr: MergeRequest) -> CodeReview:
        """Convert a MergeRequest model to a CodeReview model."""
        author = mr.author.get("name") or mr.author.get("username") or "Unknown"
        return CodeReview(
            id=str(mr.iid),
            key=mr.display_key(),
            title=mr.title,
            state="open" if mr.state == "opened" else mr.state,
            author=author,
            source_branch=mr.source_branch,
            url=str(mr.web_url),
            created_at=mr.created_at,
            draft=mr.draft,
            adapter_type=self.source_type,
            adapter_icon=self.source_icon,
        )

    async def fetch_assigned(self) -> list[CodeReview]:
        """Fetch MRs assigned to the current user.

        Returns:
            List of CodeReview items assigned to the user.
        """
        logger.info("Fetching assigned GitLab MRs", group=self.group)
        mrs = await self._adapter.fetch_assigned_mrs(group=self.group, assignee="@me")
        return [self._convert_mr_to_code_review(mr) for mr in mrs]

    async def fetch_authored(self) -> list[CodeReview]:
        """Fetch MRs authored by the current user.

        Returns:
            List of CodeReview items authored by the user.
        """
        logger.info("Fetching authored GitLab MRs", group=self.group)
        mrs = await self._adapter.fetch_assigned_mrs(group=self.group, assignee="", author="@me")
        return [self._convert_mr_to_code_review(mr) for mr in mrs]

    async def fetch_pending_review(self) -> list[CodeReview]:
        """Fetch MRs where the current user is a reviewer.

        Returns:
            List of CodeReview items pending user's review.
        """
        logger.info("Fetching pending review GitLab MRs", group=self.group)
        mrs = await self._adapter.fetch_assigned_mrs(group=self.group, reviewer="@me")
        return [self._convert_mr_to_code_review(mr) for mr in mrs]


class GitLabCLISetupSource(SetupCapableSource):
    """Setup-only source for GitLab CLI configuration.

    Used by the setup screen to configure GitLab without needing
    a group parameter.
    """

    @property
    def adapter_type(self) -> str:
        return "cli"

    @property
    def source_type(self) -> str:
        return "gitlab"

    @property
    def source_icon(self) -> str:
        return "🦊"

    async def get_status(self) -> AdapterStatus:
        installed = shutil.which("glab") is not None
        authenticated = False
        error_message = None

        if installed:
            try:
                adapter = GitLabAdapter()
                authenticated = await adapter.check_auth()
                if not authenticated:
                    error_message = "Not authenticated"
            except Exception as e:
                error_message = str(e)
        else:
            error_message = "glab CLI not installed"

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
                description="Check if glab CLI is authenticated",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="login",
                label="Sign In",
                icon="🔑",
                description="Sign in to glab CLI interactively",
                requires_params=False,
                external_process=True,
                external_command="glab auth login",
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
