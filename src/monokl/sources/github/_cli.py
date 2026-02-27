"""GitHub CLI adapter for fetching pull requests and issues.

Provides GitHubAdapter class that uses gh CLI to fetch pull requests
and issues assigned to or authored by the current user.
"""

from monokl import get_logger
from monokl.async_utils import CLIAdapter
from monokl.exceptions import CLIAuthError
from monokl.exceptions import CLINotFoundError

logger = get_logger(__name__)


class GitHubAdapter(CLIAdapter):
    """Adapter for GitHub CLI (gh) operations.

    Fetches pull requests and issues using gh's JSON output format.

    Example:
        adapter = GitHubAdapter()

        # Check if gh is available
        if adapter.is_available():
            # Fetch PRs assigned to current user
            prs = await adapter.fetch_assigned_prs()
            for pr in prs:
                print(f"#{pr['number']}: {pr['title']}")

            # Fetch issues assigned to current user
            issues = await adapter.fetch_assigned_issues()

        # Explicitly check authentication
        is_authenticated = await adapter.check_auth()
    """

    def __init__(self) -> None:
        """Initialize GitHub adapter with cli_name='gh'."""
        super().__init__("gh")

    async def fetch_assigned_prs(self) -> list[dict]:
        """Fetch PRs assigned to current user.

        Returns:
            List of PR dictionaries
        """
        logger.info("Fetching assigned GitHub PRs")
        args = [
            "pr",
            "list",
            "--assignee",
            "@me",
            "--state",
            "open",
            "--json",
            "number,title,state,author,url,createdAt,headRefName",
        ]
        return await self.fetch_json(args)

    async def fetch_authored_prs(self) -> list[dict]:
        """Fetch PRs authored by current user.

        Returns:
            List of PR dictionaries
        """
        logger.info("Fetching authored GitHub PRs")
        args = [
            "pr",
            "list",
            "--author",
            "@me",
            "--state",
            "open",
            "--json",
            "number,title,state,author,url,createdAt,headRefName",
        ]
        return await self.fetch_json(args)

    async def fetch_pending_review_prs(self) -> list[dict]:
        """Fetch PRs where current user is requested to review.

        Returns:
            List of PR dictionaries
        """
        logger.info("Fetching pending review GitHub PRs")
        args = [
            "search",
            "prs",
            "--",
            "review-requested:@me",
            "state:open",
            "--json",
            "number,title,state,author,url,createdAt,headRefName",
        ]
        return await self.fetch_json(args)

    async def fetch_assigned_issues(self) -> list[dict]:
        """Fetch issues assigned to current user.

        Returns:
            List of issue dictionaries
        """
        logger.info("Fetching assigned GitHub issues")
        args = [
            "issue",
            "list",
            "--assignee",
            "@me",
            "--state",
            "open",
            "--json",
            "number,title,state,author,url,createdAt,labels,assignees",
        ]
        return await self.fetch_json(args)

    async def check_auth(self) -> bool:
        """Check if gh is authenticated.

        Runs gh auth status to verify authentication without
        triggering any interactive prompts.

        Returns:
            True if gh is authenticated, False otherwise

        Example:
            adapter = GitHubAdapter()

            if await adapter.check_auth():
                prs = await adapter.fetch_assigned_prs()
            else:
                print("Please run: gh auth login")
        """
        logger.debug("Checking GitHub authentication")
        try:
            await self.run(["auth", "status"], check=True, timeout=5.0)
            logger.debug("GitHub authenticated")
            return True
        except (CLIAuthError, CLINotFoundError, TimeoutError):
            logger.warning("GitHub not authenticated")
            return False
