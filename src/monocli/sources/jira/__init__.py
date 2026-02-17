"""Jira source for work items.

Provides JiraSource for fetching work items from Jira.
Implements PieceOfWorkSource protocol.
"""

from monocli import get_logger
from monocli.models import PieceOfWork
from monocli.sources.base import PieceOfWorkSource

from ._cli import JiraAdapter

logger = get_logger(__name__)


class JiraSource(PieceOfWorkSource):
    """Source for Jira work items.

    Wraps the existing JiraAdapter to provide PieceOfWork items.

    Example:
        source = JiraSource(base_url="https://company.atlassian.net")

        # Check if available
        if await source.is_available():
            # Fetch assigned work items
            items = await source.fetch_items()
            for item in items:
                print(f"{item.display_key()}: {item.title}")
    """

    def __init__(self, base_url: str) -> None:
        """Initialize the Jira piece of work source.

        Args:
            base_url: Jira base URL (e.g., "https://company.atlassian.net")
        """
        self._adapter = JiraAdapter(base_url)

    @property
    def source_type(self) -> str:
        """Return the source type identifier."""
        return "jira"

    @property
    def source_icon(self) -> str:
        """Return the source icon emoji."""
        return "🔴"

    async def is_available(self) -> bool:
        """Check if acli CLI is installed."""
        return self._adapter.is_available()

    async def check_auth(self) -> bool:
        """Check if acli is authenticated."""
        return await self._adapter.check_auth()

    async def fetch_items(self) -> list[PieceOfWork]:
        """Fetch work items from Jira.

        Returns:
            List of PieceOfWork items from Jira.
        """
        logger.info("Fetching Jira work items")
        items = await self._adapter.fetch_assigned_items()
        return items  # type: ignore[return-value]
