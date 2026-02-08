"""Jira CLI adapter for fetching work items.

Provides JiraAdapter class that uses acli CLI to fetch Jira issues
assigned to the current user.
"""

from monocli.async_utils import CLIAdapter
from monocli.exceptions import CLIAuthError, CLINotFoundError
from monocli.models import JiraWorkItem


class JiraAdapter(CLIAdapter):
    """Adapter for Jira CLI (acli) operations.

    Fetches Jira work items using acli's JSON output format and validates
    them into Pydantic JiraWorkItem models.

    Example:
        adapter = JiraAdapter()

        # Check if acli is available
        if adapter.is_available():
            # Fetch issues assigned to current user
            issues = await adapter.fetch_assigned_items()
            for issue in issues:
                print(f"{issue.display_key()}: {issue.summary}")

        # Explicitly check authentication
        is_authenticated = await adapter.check_auth()
    """

    def __init__(self) -> None:
        """Initialize Jira adapter with cli_name='acli'."""
        super().__init__("acli")

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
            adapter = JiraAdapter()

            # Fetch all issues not done assigned to current user
            issues = await adapter.fetch_assigned_items()

            # Fetch only "In Progress" items
            in_progress = await adapter.fetch_assigned_items(status_filter="In Progress")
        """
        args = [
            "jira",
            "workitem",
            "search",
            "--jql",
            "assignee = currentUser() AND statusCategory != Done",
            "--json",
        ]
        return await self.fetch_and_parse(args, JiraWorkItem)

    async def check_auth(self) -> bool:
        """Check if acli is authenticated.

        Runs acli jira auth status to verify authentication without
        triggering any interactive prompts.

        Returns:
            True if acli is authenticated, False otherwise

        Example:
            adapter = JiraAdapter()

            if await adapter.check_auth():
                issues = await adapter.fetch_assigned_items()
            else:
                print("Please run: acli login")
        """
        try:
            await self.run(["jira", "auth", "status"], check=True)
            return True
        except (CLIAuthError, CLINotFoundError):
            return False
