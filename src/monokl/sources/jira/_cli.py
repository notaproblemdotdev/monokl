"""Jira CLI adapter for fetching work items.

Provides JiraAdapter class that uses acli CLI to fetch Jira issues
assigned to the current user.
"""

from monokl import get_logger
from monokl.async_utils import CLIAdapter
from monokl.exceptions import CLIAuthError
from monokl.exceptions import CLINotFoundError
from monokl.models import JiraWorkItem

logger = get_logger(__name__)


class JiraAdapter(CLIAdapter):
    """Adapter for Jira CLI (acli) operations.

    Fetches Jira work items using acli's JSON output format and validates
    them into Pydantic JiraWorkItem models.

    Example:
        adapter = JiraAdapter(base_url="https://company.atlassian.net")

        # Check if acli is available
        if adapter.is_available():
            # Fetch issues assigned to current user
            issues = await adapter.fetch_assigned_items()
            for issue in issues:
                print(f"{issue.display_key()}: {issue.summary}")

        # Explicitly check authentication
        is_authenticated = await adapter.check_auth()
    """

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize Jira adapter with base URL.

        Args:
            base_url: Optional Jira base URL (e.g., "https://company.atlassian.net")
        """
        super().__init__("acli")
        self.base_url = base_url.rstrip("/") if base_url else None

    async def fetch_assigned_items(
        self,
        status_filter: str = "!=Done",
        assignee: str = "@me",
    ) -> list[JiraWorkItem]:
        """Fetch Jira issues assigned to current user.

        Uses acli jira workitem search with --jql and --json flags to fetch issues.
        Filters by assignee and status to show only relevant items.

        Args:
            status_filter: Status filter (e.g., "!=Done", "In Progress")
            assignee: Assignee filter ("@me" for current user, or username)

        Returns:
            List of validated JiraWorkItem models

        Raises:
            CLINotFoundError: If acli is not installed
            CLIAuthError: If acli is not authenticated

        Example:
            adapter = JiraAdapter(base_url="https://company.atlassian.net")

            # Fetch all issues not done assigned to current user
            issues = await adapter.fetch_assigned_items()

            # Fetch only "In Progress" items
            in_progress = await adapter.fetch_assigned_items(status_filter="In Progress")
        """
        logger.info("Fetching Jira work items", assignee=assignee, status_filter=status_filter)
        args = [
            "jira",
            "workitem",
            "search",
            "--jql",
            "assignee = currentUser() AND statusCategory != Done",
            "--fields",
            "issuetype,key,assignee,priority,status,summary",
            "--json",
        ]
        try:
            items = await self.fetch_and_parse(args, JiraWorkItem)
            if self.base_url:
                for item in items:
                    item.base_url = self.base_url
            logger.info("Fetched Jira work items", count=len(items))
            return items
        except (CLIAuthError, CLINotFoundError):
            logger.warning("Failed to fetch Jira work items")
            raise

    async def check_auth(self) -> bool:
        """Check if acli is authenticated.

        Runs acli jira auth status to verify authentication without
        triggering any interactive prompts.

        Returns:
            True if acli is authenticated, False otherwise

        Example:
            adapter = JiraAdapter(base_url="https://company.atlassian.net")

            if await adapter.check_auth():
                issues = await adapter.fetch_assigned_items()
            else:
                print("Please run: acli jira auth login")
        """
        logger.debug("Checking Jira authentication")
        try:
            # Use shorter timeout for auth check (5s)
            await self.run(["jira", "auth", "status"], check=True, timeout=5.0)
            logger.debug("Jira authenticated")
            return True
        except (CLIAuthError, CLINotFoundError, TimeoutError):
            logger.warning("Jira not authenticated")
            return False
