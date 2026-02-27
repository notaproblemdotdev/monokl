"""GitHub source for code reviews and work items.

Provides GitHubSource for fetching pull requests and issues from GitHub.
Implements both CodeReviewSource and PieceOfWorkSource protocols.
"""

from __future__ import annotations

import shutil
from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING

from monokl import get_logger
from monokl.models import CodeReview
from monokl.models import PieceOfWork
from monokl.sources.base import AdapterStatus
from monokl.sources.base import CodeReviewSource
from monokl.sources.base import PieceOfWorkSource
from monokl.sources.base import SetupAction
from monokl.sources.base import SetupCapableSource
from monokl.sources.base import SetupParam
from monokl.sources.base import SetupResult

from ._cli import GitHubAdapter

logger = get_logger(__name__)


class GitHubSource(CodeReviewSource, PieceOfWorkSource, SetupCapableSource):
    """Source for GitHub pull requests and issues.

    Implements both CodeReviewSource (for PRs) and PieceOfWorkSource (for issues).
    Uses the gh CLI for data fetching.

    Example:
        source = GitHubSource()

        # Check if available
        if await source.is_available():
            # Fetch code reviews (PRs)
            prs = await source.fetch_assigned()

            # Fetch work items (issues)
            issues = await source.fetch_items()
    """

    def __init__(self) -> None:
        """Initialize the GitHub source."""
        self._adapter = GitHubAdapter()

    @property
    def source_type(self) -> str:
        return "github"

    @property
    def source_icon(self) -> str:
        return "🐙"

    @property
    def adapter_type(self) -> str:
        return "cli"

    async def is_available(self) -> bool:
        return self._adapter.is_available()

    async def check_auth(self) -> bool:
        return await self._adapter.check_auth()

    async def get_status(self) -> AdapterStatus:
        installed = shutil.which("gh") is not None
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
            error_message = "gh CLI not installed"

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
                description="Check if gh CLI is authenticated",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="login",
                label="Sign In",
                icon="🔑",
                description="Sign in to gh CLI interactively",
                requires_params=False,
                external_process=True,
                external_command="gh auth login",
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

    async def fetch_assigned(self) -> list[CodeReview]:
        """Fetch PRs assigned to the current user.

        Returns:
            List of CodeReview items (PRs) assigned to the user.
        """
        logger.info("Fetching assigned GitHub PRs")
        data = await self._adapter.fetch_assigned_prs()
        return [self._convert_pr_to_code_review(pr) for pr in data]

    async def fetch_authored(self) -> list[CodeReview]:
        """Fetch PRs authored by the current user.

        Returns:
            List of CodeReview items (PRs) authored by the user.
        """
        logger.info("Fetching authored GitHub PRs")
        data = await self._adapter.fetch_authored_prs()
        return [self._convert_pr_to_code_review(pr) for pr in data]

    async def fetch_pending_review(self) -> list[CodeReview]:
        """Fetch PRs where the current user is requested to review.

        Returns:
            List of CodeReview items (PRs) pending user's review.
        """
        logger.info("Fetching pending review GitHub PRs")
        data = await self._adapter.fetch_pending_review_prs()
        return [self._convert_pr_to_code_review(pr) for pr in data]

    async def fetch_items(self) -> list[PieceOfWork]:
        """Fetch issues assigned to the current user.

        Returns:
            List of PieceOfWork items (issues) assigned to the user.
        """
        logger.info("Fetching assigned GitHub issues")
        data = await self._adapter.fetch_assigned_issues()
        return [self._convert_issue_to_piece_of_work(issue) for issue in data]

    def _convert_pr_to_code_review(self, pr: dict) -> CodeReview:
        """Convert a GitHub PR dict to a CodeReview model."""
        author = pr.get("author", {}).get("login", "Unknown")
        created_at = None
        if pr.get("createdAt"):
            with suppress(ValueError, AttributeError):
                created_at = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))

        return CodeReview(
            id=str(pr["number"]),
            key=f"#{pr['number']}",
            title=pr["title"],
            state=pr.get("state", "open").lower(),
            author=author,
            source_branch=pr.get("headRefName", ""),
            url=pr["url"],
            created_at=created_at,
            draft=pr.get("draft", False),
            adapter_type=self.source_type,
            adapter_icon=self.source_icon,
        )

    def _convert_issue_to_piece_of_work(self, issue: dict) -> PieceOfWork:
        """Convert a GitHub issue dict to a PieceOfWork model."""
        from monokl.models import GitHubPieceOfWork

        return GitHubPieceOfWork(
            number=issue["number"],
            title=issue["title"],
            state=issue.get("state", "open"),
            author=issue.get("author", {}),
            html_url=issue["url"],
            labels=issue.get("labels", []),
            assignees=issue.get("assignees", []),
        )


class GitHubCLISetupSource(SetupCapableSource):
    """Setup-only source for GitHub CLI configuration."""

    @property
    def adapter_type(self) -> str:
        return "cli"

    @property
    def source_type(self) -> str:
        return "github"

    @property
    def source_icon(self) -> str:
        return "🐙"

    async def get_status(self) -> AdapterStatus:
        installed = shutil.which("gh") is not None
        authenticated = False
        error_message = None

        if installed:
            try:
                adapter = GitHubAdapter()
                authenticated = await adapter.check_auth()
                if not authenticated:
                    error_message = "Not authenticated"
            except Exception as e:
                error_message = str(e)
        else:
            error_message = "gh CLI not installed"

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
                description="Check if gh CLI is authenticated",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="login",
                label="Sign In",
                icon="🔑",
                description="Sign in to gh CLI interactively",
                requires_params=False,
                external_process=True,
                external_command="gh auth login",
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
