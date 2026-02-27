"""GitLab CLI adapter for fetching merge requests.

Provides GitLabAdapter class that uses glab CLI to fetch merge requests
assigned to or authored by the current user.
"""

from monokl import get_logger
from monokl.async_utils import CLIAdapter
from monokl.async_utils import run_cli_command
from monokl.exceptions import CLIAuthError
from monokl.exceptions import CLINotFoundError
from monokl.models import MergeRequest

logger = get_logger(__name__)


class GitLabAdapter(CLIAdapter):
    """Adapter for GitLab CLI (glab) operations.

        Fetches merge requests using glab's JSON output format and validates
    them into Pydantic MergeRequest models.

    Example:
            adapter = GitLabAdapter()

            # Check if glab is available
            if adapter.is_available():
                # Fetch MRs assigned to current user
                mrs = await adapter.fetch_assigned_mrs()
                for mr in mrs:
                    print(f"{mr.display_key()}: {mr.title}")

            # Explicitly check authentication
            is_authenticated = await adapter.check_auth()
    """

    def __init__(self) -> None:
        """Initialize GitLab adapter with cli_name='glab'."""
        super().__init__("glab")

    async def fetch_assigned_mrs(
        self,
        group: str | None = None,
        assignee: str = "@me",
        author: str | None = None,
        reviewer: str | None = None,
        state: str | None = None,
    ) -> list[MergeRequest]:
        """Fetch MRs assigned to current user.

        Uses glab mr list with --output json to fetch merge requests.
        Filters by assignee, author, reviewer, state, and group to show only relevant MRs.

        Args:
            group: Optional GitLab group to search (e.g., "axpo-pl")
            assignee: Assignee filter ("@me" for current user, or username)
            author: Optional author filter (username)
            reviewer: Optional reviewer filter ("@me" for current user, or username)
            state: Optional state filter ("opened", "closed", "merged", "locked")

        Returns:
            List of validated MergeRequest models

        Raises:
            CLINotFoundError: If glab is not installed
            CLIAuthError: If glab is not authenticated
            CLIError: If glab returns an error (e.g., no git remotes found)

        Example:
            adapter = GitLabAdapter()

            # Fetch all open MRs assigned to current user
            mrs = await adapter.fetch_assigned_mrs(group="my-group")

            # Fetch merged MRs by specific author
            mrs = await adapter.fetch_assigned_mrs(
                group="my-group",
                author="alice",
                state="merged"
            )

            # Fetch MRs where current user is a reviewer
            mrs = await adapter.fetch_assigned_mrs(group="my-group", reviewer="@me")
        """
        # Without an explicit group, glab relies on git remotes.
        # Skip fetch when the current repo has no GitLab remote to avoid noisy errors.
        if not group and not await self._has_gitlab_remote():
            logger.info("Skipping GitLab MR fetch: no group configured and no GitLab remote")
            return []

        logger.info(
            "Fetching merge requests",
            group=group,
            assignee=assignee,
            author=author,
            state=state,
        )
        args = [
            "mr",
            "list",
            "--all",
            "--output",
            "json",
        ]

        if group:
            args.extend(["--group", group])

        # Add assignee filter (if empty string, don't add to args to avoid glab conflict)
        if assignee:
            args.extend(["--assignee", assignee])

        # Add optional filters
        if author:
            args.extend(["--author", author])

        if reviewer:
            args.extend(["--reviewer", reviewer])

        if state:
            # Map state values to glab flags
            state_flag_map = {
                "opened": "--open",
                "closed": "--closed",
                "merged": "--merged",
            }
            if state in state_flag_map:
                args.append(state_flag_map[state])
            # Note: glab doesn't have a --locked flag, we filter post-fetch if needed

        try:
            result = await self.fetch_and_parse(args, MergeRequest)
            logger.info("Fetched merge requests", count=len(result))
            return result
        except CLIAuthError:
            logger.warning(
                "Failed to fetch merge requests - authentication error",
                group=group,
            )
            raise
        except CLINotFoundError:
            logger.warning(
                "Failed to fetch merge requests - glab not found",
                group=group,
            )
            raise

    async def _has_gitlab_remote(self) -> bool:
        """Check whether current repository has at least one GitLab remote."""
        try:
            stdout, _ = await run_cli_command(["git", "remote", "-v"], check=False, timeout=5.0)
        except Exception:
            return False

        return "gitlab" in stdout.lower()

    async def check_auth(self) -> bool:
        """Check if glab is authenticated.

        Runs glab auth status to verify authentication without
        triggering any interactive prompts.

        Returns:
            True if glab is authenticated, False otherwise

        Example:
            adapter = GitLabAdapter()

            if await adapter.check_auth():
                mrs = await adapter.fetch_assigned_mrs()
            else:
                print("Please run: glab auth login")
        """
        logger.debug("Checking GitLab authentication")
        try:
            # Use shorter timeout for auth check (5s) and don't raise on error
            await self.run(["auth", "status"], check=True, timeout=5.0)
            logger.debug("GitLab authenticated")
            return True
        except (CLIAuthError, CLINotFoundError, TimeoutError):
            logger.warning("GitLab not authenticated")
            return False
