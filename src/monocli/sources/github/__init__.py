"""GitHub source for code reviews and work items.

Provides GitHubSource for fetching pull requests and issues from GitHub.
Implements both CodeReviewSource and PieceOfWorkSource protocols.
"""

from contextlib import suppress
from datetime import datetime

from monocli import get_logger
from monocli.models import CodeReview, PieceOfWork
from monocli.sources.base import CodeReviewSource, PieceOfWorkSource

from ._cli import GitHubAdapter

logger = get_logger(__name__)


class GitHubSource(CodeReviewSource, PieceOfWorkSource):
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
        """Return the source type identifier."""
        return "github"

    @property
    def source_icon(self) -> str:
        """Return the source icon emoji."""
        return "🐙"

    async def is_available(self) -> bool:
        """Check if gh CLI is installed."""
        return self._adapter.is_available()

    async def check_auth(self) -> bool:
        """Check if gh is authenticated."""
        return await self._adapter.check_auth()

    async def fetch_assigned(self) -> list[CodeReview]:
        """Fetch PRs assigned to the current user.

        Returns:
            List of CodeReview items (PRs) assigned to the user.
        """
        logger.info("Fetching assigned GitHub PRs")
        try:
            data = await self._adapter.fetch_assigned_prs()
            return [self._convert_pr_to_code_review(pr) for pr in data]
        except Exception as e:
            logger.warning("Failed to fetch assigned GitHub PRs", error=str(e))
            return []

    async def fetch_authored(self) -> list[CodeReview]:
        """Fetch PRs authored by the current user.

        Returns:
            List of CodeReview items (PRs) authored by the user.
        """
        logger.info("Fetching authored GitHub PRs")
        try:
            data = await self._adapter.fetch_authored_prs()
            return [self._convert_pr_to_code_review(pr) for pr in data]
        except Exception as e:
            logger.warning("Failed to fetch authored GitHub PRs", error=str(e))
            return []

    async def fetch_pending_review(self) -> list[CodeReview]:
        """Fetch PRs where the current user is requested to review.

        Returns:
            List of CodeReview items (PRs) pending user's review.
        """
        logger.info("Fetching pending review GitHub PRs")
        try:
            data = await self._adapter.fetch_pending_review_prs()
            return [self._convert_pr_to_code_review(pr) for pr in data]
        except Exception as e:
            logger.warning("Failed to fetch pending review GitHub PRs", error=str(e))
            return []

    async def fetch_items(self) -> list[PieceOfWork]:
        """Fetch issues assigned to the current user.

        Returns:
            List of PieceOfWork items (issues) assigned to the user.
        """
        logger.info("Fetching assigned GitHub issues")
        try:
            data = await self._adapter.fetch_assigned_issues()
            return [self._convert_issue_to_piece_of_work(issue) for issue in data]
        except Exception as e:
            logger.warning("Failed to fetch GitHub issues", error=str(e))
            return []

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
        from monocli.models import GitHubPieceOfWork

        return GitHubPieceOfWork(
            number=issue["number"],
            title=issue["title"],
            state=issue.get("state", "open"),
            author=issue.get("author", {}),
            html_url=issue["url"],
            labels=issue.get("labels", []),
            assignees=issue.get("assignees", []),
        )
