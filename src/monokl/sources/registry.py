"""Source registry for managing and fetching from multiple data sources.

Provides SourceRegistry for discovering, registering, and fetching data
from multiple sources concurrently.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from monokl import get_logger

if TYPE_CHECKING:
    from monokl.models import CodeReview
    from monokl.models import PieceOfWork
    from monokl.sources.base import CodeReviewSource
    from monokl.sources.base import PieceOfWorkSource

logger = get_logger(__name__)


class SourceRegistry:
    """Registry for managing multiple data sources.

    Provides methods for registering sources and fetching data from
    all registered sources concurrently.

    Example:
        registry = SourceRegistry()

        # Register code review sources
        registry.register_code_review_source(GitLabSource(group="my-group"))
        registry.register_code_review_source(GitHubSource())

        # Register work item sources
        registry.register_piece_of_work_source(JiraSource())
        registry.register_piece_of_work_source(TodoistSource(token="xxx"))

        # Fetch from all sources
        code_reviews = await registry.fetch_all_code_reviews()
        work_items = await registry.fetch_all_piece_of_work()
    """

    def __init__(self) -> None:
        """Initialize the source registry."""
        self._code_review_sources: list[CodeReviewSource] = []
        self._piece_of_work_sources: list[PieceOfWorkSource] = []

    def register_code_review_source(self, source: CodeReviewSource) -> None:
        """Register a code review source.

        Args:
            source: Source implementing CodeReviewSource protocol.
        """
        self._code_review_sources.append(source)
        logger.debug(
            "Registered code review source",
            source_type=source.source_type,
        )

    def register_piece_of_work_source(self, source: PieceOfWorkSource) -> None:
        """Register a piece of work source.

        Args:
            source: Source implementing PieceOfWorkSource protocol.
        """
        self._piece_of_work_sources.append(source)
        logger.debug(
            "Registered piece of work source",
            source_type=source.source_type,
        )

    def get_code_review_sources(self) -> list[CodeReviewSource]:
        """Get all registered code review sources.

        Returns:
            List of registered CodeReviewSource instances.
        """
        return self._code_review_sources.copy()

    def get_piece_of_work_sources(self) -> list[PieceOfWorkSource]:
        """Get all registered piece of work sources.

        Returns:
            List of registered PieceOfWorkSource instances.
        """
        return self._piece_of_work_sources.copy()

    async def fetch_all_code_reviews(
        self,
        include_assigned: bool = True,
        include_authored: bool = True,
        include_pending_review: bool = True,
    ) -> dict[str, list[CodeReview]]:
        """Fetch code reviews from all registered sources.

        Args:
            include_assigned: Whether to fetch assigned code reviews.
            include_authored: Whether to fetch authored code reviews.
            include_pending_review: Whether to fetch pending review code reviews.

        Returns:
            Dictionary mapping source type to list of CodeReview items.
        """
        results: dict[str, list[CodeReview]] = {}

        async def fetch_from_source(source: CodeReviewSource) -> tuple[str, list[CodeReview]]:
            """Fetch from a single source."""
            try:
                # Check if source is available and authenticated
                if not await source.is_available():
                    logger.debug(
                        "Source not available, skipping",
                        source_type=source.source_type,
                    )
                    return source.source_type, []

                if not await source.check_auth():
                    logger.debug(
                        "Source not authenticated, skipping",
                        source_type=source.source_type,
                    )
                    return source.source_type, []

                # Fetch from source
                all_reviews: list[CodeReview] = []

                if include_assigned:
                    try:
                        assigned = await source.fetch_assigned()
                        all_reviews.extend(assigned)
                        logger.debug(
                            "Fetched assigned code reviews",
                            source_type=source.source_type,
                            count=len(assigned),
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to fetch assigned code reviews",
                            source_type=source.source_type,
                            error=str(e),
                        )

                if include_pending_review:
                    try:
                        pending = await source.fetch_pending_review()
                        all_reviews.extend(pending)
                        logger.debug(
                            "Fetched pending review code reviews",
                            source_type=source.source_type,
                            count=len(pending),
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to fetch pending review code reviews",
                            source_type=source.source_type,
                            error=str(e),
                        )

                if include_authored:
                    try:
                        authored = await source.fetch_authored()
                        all_reviews.extend(authored)
                        logger.debug(
                            "Fetched authored code reviews",
                            source_type=source.source_type,
                            count=len(authored),
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to fetch authored code reviews",
                            source_type=source.source_type,
                            error=str(e),
                        )

                return source.source_type, all_reviews

            except Exception as e:
                logger.error(
                    "Failed to fetch from source",
                    source_type=source.source_type,
                    error=str(e),
                )
                return source.source_type, []

        # Fetch from all sources concurrently
        tasks = [fetch_from_source(source) for source in self._code_review_sources]

        for source_type, reviews in await asyncio.gather(*tasks):
            if reviews:
                if source_type in results:
                    results[source_type].extend(reviews)
                else:
                    results[source_type] = reviews

        return results

    async def fetch_all_piece_of_work(self) -> dict[str, list[PieceOfWork]]:
        """Fetch piece of work items from all registered sources.

        Returns:
            Dictionary mapping source type to list of PieceOfWork items.
        """
        results: dict[str, list[PieceOfWork]] = {}

        async def fetch_from_source(source: PieceOfWorkSource) -> tuple[str, list[PieceOfWork]]:
            """Fetch from a single source."""
            try:
                # Check if source is available and authenticated
                if not await source.is_available():
                    logger.debug(
                        "Source not available, skipping",
                        source_type=source.source_type,
                    )
                    return source.source_type, []

                if not await source.check_auth():
                    logger.debug(
                        "Source not authenticated, skipping",
                        source_type=source.source_type,
                    )
                    return source.source_type, []

                # Fetch from source
                items = await source.fetch_items()
                logger.debug(
                    "Fetched piece of work items",
                    source_type=source.source_type,
                    count=len(items),
                )

                return source.source_type, items

            except Exception as e:
                logger.error(
                    "Failed to fetch from source",
                    source_type=source.source_type,
                    error=str(e),
                )
                return source.source_type, []

        # Fetch from all sources concurrently
        tasks = [fetch_from_source(source) for source in self._piece_of_work_sources]

        for source_type, items in await asyncio.gather(*tasks):
            if items:
                if source_type in results:
                    results[source_type].extend(items)
                else:
                    results[source_type] = items

        return results
