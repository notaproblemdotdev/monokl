"""GitLab code review source.

Provides GitLabCodeReviewSource for fetching merge requests from GitLab.
"""

from monocli import get_logger
from monocli.adapters.gitlab import GitLabAdapter
from monocli.models import CodeReview, MergeRequest
from monocli.sources.base import CodeReviewSource

# Type alias for clarity in this module
MergeRequestModel = MergeRequest

logger = get_logger(__name__)


class GitLabCodeReviewSource(CodeReviewSource):
    """Source for GitLab merge requests (code reviews).

    Wraps the existing GitLabAdapter to provide CodeReview items.

    Example:
        source = GitLabCodeReviewSource(group="my-group")

        # Check if available
        if await source.is_available():
            # Fetch assigned MRs
            mrs = await source.fetch_assigned()
            for mr in mrs:
                print(f"{mr.display_key()}: {mr.title}")
    """

    def __init__(self, group: str) -> None:
        """Initialize the GitLab code review source.

        Args:
            group: GitLab group to search (e.g., "my-group")
        """
        self.group = group
        self._adapter = GitLabAdapter()

    @property
    def source_type(self) -> str:
        """Return the source type identifier."""
        return "gitlab"

    @property
    def source_icon(self) -> str:
        """Return the source icon emoji."""
        return "🦊"

    async def is_available(self) -> bool:
        """Check if glab CLI is installed."""
        return self._adapter.is_available()

    async def check_auth(self) -> bool:
        """Check if glab is authenticated."""
        return await self._adapter.check_auth()

    def _convert_mr_to_code_review(self, mr: MergeRequestModel) -> CodeReview:
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
