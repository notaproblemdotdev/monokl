"""WorkStore - unified data access with transparent caching.

Provides high-level API for fetching code reviews and work items
with automatic caching, background refresh, and source health tracking.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal

from monocle import get_logger
from monocle.db._cache_backend import _CacheBackend
from monocle.db._source_health import _SourceHealth
from monocle.models import CodeReview
from monocle.models import JiraWorkItem
from monocle.models import TodoistTask

if TYPE_CHECKING:
    from monocle.models import PieceOfWork
    from monocle.sources.base import CodeReviewSource
    from monocle.sources.base import PieceOfWorkSource
    from monocle.sources.registry import SourceRegistry

logger = get_logger(__name__)

# Default TTL values (in seconds)
DEFAULT_CODE_REVIEW_TTL = 300  # 5 minutes
DEFAULT_WORK_ITEM_TTL = 600  # 10 minutes
DEFAULT_BACKGROUND_TIMEOUT = 30  # 30 seconds


@dataclass(frozen=True)
class FetchResult[T]:
    """Result of a fetch operation with metadata.

    Attributes:
        data: Fetched items (from cache or API).
        fresh: True if data was fetched from API, False if from cache.
        failed_sources: List of source names that failed this fetch.
        errors: Dictionary mapping failed source names to error messages.
    """

    data: list[T]
    fresh: bool
    failed_sources: list[str]
    errors: dict[str, str]


class WorkStore:
    """Unified data access layer with transparent caching.

    Provides automatic fetch-cache-orchestration with background refresh
    and source health tracking. Callers just request data; WorkStore
    handles freshness, fetching, caching, and stale fallbacks.

    Args:
        source_registry: Registry of data sources to fetch from.
        code_review_ttl: TTL in seconds for code review cache.
        work_item_ttl: TTL in seconds for work item cache.
        background_timeout: Timeout in seconds for background refresh.
        cleanup_days: Days before cleaning up old cache records.

    Example:
        store = WorkStore(source_registry)

        # Get code reviews (auto-fetches if cache stale)
        result = await store.get_code_reviews("assigned")
        if result.failed_sources:
            print(f"Warning: {result.failed_sources} failed")

        # Force refresh
        result = await store.get_code_reviews("assigned", force_refresh=True)

        # Invalidate specific source
        await store.invalidate(data_type="code_reviews", source="github")
    """

    def __init__(
        self,
        source_registry: SourceRegistry,
        code_review_ttl: int = DEFAULT_CODE_REVIEW_TTL,
        work_item_ttl: int = DEFAULT_WORK_ITEM_TTL,
        background_timeout: int = DEFAULT_BACKGROUND_TIMEOUT,
        cleanup_days: int = 30,
    ) -> None:
        self._registry = source_registry
        self._code_review_ttl = code_review_ttl
        self._work_item_ttl = work_item_ttl
        self._background_timeout = background_timeout
        self._cache = _CacheBackend(cleanup_days=cleanup_days)
        self._health = _SourceHealth()
        self._background_tasks: set[asyncio.Task] = set()

    async def get_code_reviews(
        self,
        subsection: Literal["assigned", "opened"],
        *,
        force_refresh: bool = False,
    ) -> FetchResult[CodeReview]:
        """Get code reviews with automatic fetch/cache/background refresh.

        Returns fresh data if available in cache. If cache is stale,
        returns stale data immediately and triggers background refresh.
        If cache is empty, fetches from sources.

        Args:
            subsection: "assigned" for MRs assigned to user,
                       "opened" for MRs authored by user.
            force_refresh: If True, bypass cache and fetch fresh data.

        Returns:
            FetchResult with code reviews and metadata.
        """
        if force_refresh:
            return await self._fetch_code_reviews(subsection)

        cached_result = await self._get_cached_code_reviews(subsection)
        if cached_result is None:
            return await self._fetch_code_reviews(subsection)

        cached_data, cached_errors = cached_result
        all_reviews: list[CodeReview] = self._flatten_cached_data(cached_data)
        is_fresh = await self._is_any_fresh("code_reviews", subsection)

        if not is_fresh:
            self._trigger_background_refresh(data_type="code_reviews", subsection=subsection)

        # Sources with cached data that have errors are considered "failed"
        failed_sources = list(cached_errors.keys())

        return FetchResult(
            data=all_reviews,
            fresh=False,
            failed_sources=failed_sources,
            errors=cached_errors,
        )

    async def get_work_items(
        self,
        *,
        force_refresh: bool = False,
    ) -> FetchResult[PieceOfWork]:
        """Get work items with automatic fetch/cache/background refresh.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data.

        Returns:
            FetchResult with work items and metadata.
        """
        if force_refresh:
            return await self._fetch_work_items()

        cached_result = await self._get_cached_work_items()
        if cached_result is None:
            return await self._fetch_work_items()

        cached_data, cached_errors = cached_result
        all_items: list[PieceOfWork] = self._flatten_cached_data(cached_data)
        is_fresh = await self._is_any_fresh("work_items")

        if not is_fresh:
            self._trigger_background_refresh(data_type="work_items")

        # Sources with cached data that have errors are considered "failed"
        failed_sources = list(cached_errors.keys())

        return FetchResult(
            data=all_items,
            fresh=False,
            failed_sources=failed_sources,
            errors=cached_errors,
        )

    async def invalidate(
        self,
        *,
        data_type: Literal["code_reviews", "work_items"] | None = None,
        source: str | None = None,
    ) -> None:
        """Invalidate cache with fine-grained control.

        Args:
            data_type: Filter by data type, or None for all types.
            source: Filter by source name, or None for all sources.

        Examples:
            await store.invalidate()  # All caches
            await store.invalidate(data_type="code_reviews")  # All code reviews
            await store.invalidate(source="github")  # All github data
            await store.invalidate(data_type="code_reviews", source="github")
        """
        await self._cache.invalidate(data_type=data_type, source=source)

    async def is_fresh(
        self,
        data_type: Literal["code_reviews", "work_items"],
        source: str | None = None,
    ) -> bool:
        """Check if cache is fresh for a data type.

        Args:
            data_type: Type of data to check.
            source: Specific source to check, or None for all sources.

        Returns:
            True if cache is fresh, False otherwise.
        """
        if not source:
            # Check all sources for this data type
            return await self._is_any_fresh(data_type)

        if data_type == "code_reviews":
            # Check both subsections
            assigned_key = f"code_reviews:{source}:assigned"
            opened_key = f"code_reviews:{source}:opened"
            assigned_fresh = await self._cache.is_fresh(assigned_key)
            opened_fresh = await self._cache.is_fresh(opened_key)
            return assigned_fresh and opened_fresh
        key = f"work_items:{source}"
        return await self._cache.is_fresh(key)

    def _flatten_cached_data(self, cached_data: dict[str, list[Any]]) -> list[Any]:
        """Flatten cached data from all sources into a single list.

        Args:
            cached_data: Dictionary mapping source names to lists of items.

        Returns:
            Flattened list of all items.
        """
        return [item for source_items in cached_data.values() for item in source_items]

    async def _get_cached_code_reviews(
        self,
        subsection: str,
    ) -> tuple[dict[str, list[CodeReview]], dict[str, str]] | None:
        """Get cached code reviews from all sources.

        Returns:
            Tuple of (data dict, errors dict) or None if no cached data.
        """
        result: dict[str, list[CodeReview]] = {}
        errors: dict[str, str] = {}

        for source in self._registry.get_code_review_sources():
            source_type = source.source_type
            cache_key = f"code_reviews:{source_type}:{subsection}"

            cached = await self._cache.get(cache_key, accept_stale=True)
            if cached is None:
                continue

            reviews = self._deserialize_code_reviews(cached, source_type)
            if reviews:
                result[source_type] = reviews

            # Get error info for this source
            cache_info = await self._cache.get_cache_info(cache_key)
            if cache_info and cache_info.get("last_error"):
                errors[source_type] = cache_info["last_error"]

        return (result, errors) if result else None

    def _deserialize_code_reviews(
        self, cached: list[dict[str, Any]], source_type: str
    ) -> list[CodeReview]:
        """Deserialize cached data into CodeReview objects."""
        reviews: list[CodeReview] = []
        for item in cached:
            try:
                review = CodeReview.model_validate(item, strict=False)
                reviews.append(review)
            except Exception as e:
                logger.warning(
                    "Failed to deserialize cached review", source=source_type, error=str(e)
                )
        return reviews

    async def _get_cached_work_items(
        self,
    ) -> tuple[dict[str, list[PieceOfWork]], dict[str, str]] | None:
        """Get cached work items from all sources.

        Returns:
            Tuple of (data dict, errors dict) or None if no cached data.
        """
        result: dict[str, list[PieceOfWork]] = {}
        errors: dict[str, str] = {}

        for source in self._registry.get_piece_of_work_sources():
            source_type = source.source_type
            cache_key = f"work_items:{source_type}"

            cached = await self._cache.get(cache_key, accept_stale=True)
            if cached is None:
                continue

            items = self._deserialize_work_items(cached, source_type)
            if items:
                result[source_type] = items

            # Get error info for this source
            cache_info = await self._cache.get_cache_info(cache_key)
            if cache_info and cache_info.get("last_error"):
                errors[source_type] = cache_info["last_error"]

        return (result, errors) if result else None

    def _deserialize_work_items(
        self, cached: list[dict[str, Any]], source_type: str
    ) -> list[PieceOfWork]:
        """Deserialize cached data into PieceOfWork objects."""
        items: list[PieceOfWork] = []
        for item in cached:
            try:
                work_item = self._deserialize_single_work_item(item)
                if work_item:
                    items.append(work_item)
            except Exception as e:
                logger.warning(
                    "Failed to deserialize cached work item",
                    source=source_type,
                    error=str(e),
                )
        return items

    def _deserialize_single_work_item(self, item: dict[str, Any]) -> PieceOfWork | None:
        """Deserialize a single work item based on its adapter type."""
        adapter_type = item.get("adapter_type", item.get("source_type", ""))

        if adapter_type == "jira":
            return JiraWorkItem.model_validate(item, strict=False)
        if adapter_type == "todoist":
            return TodoistTask.model_validate(item, strict=False)

        logger.warning("Unknown work item type", type=adapter_type)
        return None

    async def _is_any_fresh(
        self,
        data_type: str,
        subsection: str | None = None,
    ) -> bool:
        """Check if any cached data is fresh using strategy pattern."""
        freshness_strategy = self._freshness_strategies.get(data_type)
        if freshness_strategy is None:
            return False
        return await freshness_strategy(subsection)

    @property
    def _freshness_strategies(self) -> dict[str, callable]:
        """Get mapping of data types to freshness check strategies."""
        return {
            "code_reviews": self._is_any_code_review_fresh,
            "work_items": self._is_any_work_item_fresh,
        }

    async def _is_any_code_review_fresh(self, subsection: str | None = None) -> bool:
        """Check if any code review cache is fresh."""
        for source in self._registry.get_code_review_sources():
            cache_key = f"code_reviews:{source.source_type}:{subsection}"
            if await self._cache.is_fresh(cache_key):
                return True
        return False

    async def _is_any_work_item_fresh(self, _subsection: str | None = None) -> bool:
        """Check if any work item cache is fresh."""
        for source in self._registry.get_piece_of_work_sources():
            cache_key = f"work_items:{source.source_type}"
            if await self._cache.is_fresh(cache_key):
                return True
        return False

    def _trigger_background_refresh(
        self,
        data_type: str,
        subsection: str | None = None,
    ) -> None:
        """Trigger background refresh of stale cache."""
        task = asyncio.create_task(
            self._background_refresh(data_type=data_type, subsection=subsection),
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _background_refresh(self, **kwargs) -> None:
        """Perform background refresh with timeout using strategy pattern.

        Args:
            **kwargs: Must include 'data_type'. For code_reviews, include 'subsection'.
        """
        data_type = kwargs.get("data_type")
        subsection = kwargs.get("subsection")

        refresh_strategy = self._refresh_strategies.get(data_type)
        if refresh_strategy is None:
            logger.warning("Unknown data type for background refresh", data_type=data_type)
            return

        try:
            async with asyncio.timeout(self._background_timeout):
                await refresh_strategy(subsection)
        except TimeoutError:
            logger.warning(
                "Background refresh timed out", data_type=data_type, subsection=subsection
            )
        except Exception as e:
            logger.error(
                "Background refresh failed",
                data_type=data_type,
                subsection=subsection,
                error=str(e),
            )

    @property
    def _refresh_strategies(self) -> dict[str, callable]:
        """Get mapping of data types to refresh strategies."""
        return {
            "code_reviews": self._fetch_code_reviews,
            "work_items": self._fetch_work_items,
        }

    async def _fetch_code_reviews(
        self,
        subsection: str,
    ) -> FetchResult[CodeReview]:
        """Fetch code reviews from all sources."""
        source_order = self._get_prioritized_sources()

        results = await self._fetch_from_all_code_review_sources(source_order, subsection)

        return self._aggregate_fetch_results(results)

    def _get_prioritized_sources(self) -> list[str]:
        """Get source names sorted by priority (failed ones first)."""
        sources = self._registry.get_code_review_sources()
        source_names = [s.source_type for s in sources]
        return self._health.get_priority_sources(source_names)

    async def _fetch_from_all_code_review_sources(
        self, source_order: list[str], subsection: str
    ) -> list[tuple[str, list[CodeReview], str | None]]:
        """Fetch from all sources concurrently and return results."""
        sources = self._registry.get_code_review_sources()
        source_map = {s.source_type: s for s in sources}

        tasks = [
            self._fetch_single_code_review_source(source_map[name], name, subsection)
            for name in source_order
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[tuple[str, list[CodeReview], str | None]] = []
        for result in raw_results:
            if isinstance(result, Exception):
                logger.error("Unexpected error fetching code reviews", error=str(result))
                continue
            results.append(result)  # type: ignore[arg-type]
        return results

    async def _fetch_single_code_review_source(
        self, source: CodeReviewSource, source_name: str, subsection: str
    ) -> tuple[str, list[CodeReview], str | None]:
        """Fetch from a single code review source."""
        try:
            reviews = await self._fetch_by_subsection(source, subsection)
            if reviews is None:
                return source_name, [], f"Failed to fetch {subsection}"

            self._health.record_success(source_name)
            await self._cache_code_reviews(source_name, subsection, reviews)
            return source_name, reviews, None

        except Exception as e:
            error_msg = str(e)
            self._health.record_failure(source_name, error_msg)
            await self._cache.record_error(
                f"code_reviews:{source_name}:{subsection}",
                error_msg,
            )
            return source_name, [], error_msg

    async def _fetch_by_subsection(
        self, source: CodeReviewSource, subsection: str
    ) -> list[CodeReview] | None:
        """Fetch code reviews based on subsection type."""
        try:
            if subsection == "assigned":
                return await source.fetch_assigned()
            if subsection == "opened":
                return await source.fetch_authored()
            logger.warning("Unknown subsection", subsection=subsection)
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch {subsection}", source=source.source_type, error=str(e))
            return None

    async def _cache_code_reviews(
        self, source_name: str, subsection: str, reviews: list[CodeReview]
    ) -> None:
        """Cache code review results."""
        if not reviews:
            return

        cache_key = f"code_reviews:{source_name}:{subsection}"
        data = [r.model_dump(mode="json", by_alias=True) for r in reviews]
        await self._cache.set(
            cache_key=cache_key,
            data=data,
            ttl_seconds=self._code_review_ttl,
            data_type="code_reviews",
            source=source_name,
            subsection=subsection,
        )

    def _aggregate_fetch_results(
        self, results: list[tuple[str, list[CodeReview], str | None]]
    ) -> FetchResult[CodeReview]:
        """Aggregate fetch results from all sources."""
        all_reviews: list[CodeReview] = []
        failed_sources: list[str] = []
        errors: dict[str, str] = {}

        for source_name, reviews, error in results:
            if error:
                failed_sources.append(source_name)
                errors[source_name] = error
            else:
                all_reviews.extend(reviews)

        return FetchResult(
            data=all_reviews,
            fresh=True,
            failed_sources=failed_sources,
            errors=errors,
        )

    async def _fetch_work_items(self) -> FetchResult[PieceOfWork]:
        """Fetch work items from all sources."""
        source_order = self._get_prioritized_work_sources()

        results = await self._fetch_from_all_work_sources(source_order)

        return self._aggregate_work_fetch_results(results)

    def _get_prioritized_work_sources(self) -> list[str]:
        """Get work source names sorted by priority (failed ones first)."""
        sources = self._registry.get_piece_of_work_sources()
        source_names = [s.source_type for s in sources]
        return self._health.get_priority_sources(source_names)

    async def _fetch_from_all_work_sources(
        self, source_order: list[str]
    ) -> list[tuple[str, list[PieceOfWork], str | None]]:
        """Fetch from all work sources concurrently and return results."""
        sources = self._registry.get_piece_of_work_sources()
        source_map = {s.source_type: s for s in sources}

        tasks = [self._fetch_single_work_source(source_map[name], name) for name in source_order]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[tuple[str, list[PieceOfWork], str | None]] = []
        for result in raw_results:
            if isinstance(result, Exception):
                logger.error("Unexpected error fetching work items", error=str(result))
                continue
            results.append(result)  # type: ignore[arg-type]
        return results

    async def _fetch_single_work_source(
        self, source: PieceOfWorkSource, source_name: str
    ) -> tuple[str, list[PieceOfWork], str | None]:
        """Fetch from a single work item source."""
        try:
            items = await source.fetch_items()
            self._health.record_success(source_name)
            await self._cache_work_items(source_name, items)
            return source_name, items, None

        except Exception as e:
            error_msg = str(e)
            self._health.record_failure(source_name, error_msg)
            await self._cache.record_error(f"work_items:{source_name}", error_msg)
            return source_name, [], error_msg

    async def _cache_work_items(self, source_name: str, items: list[PieceOfWork]) -> None:
        """Cache work item results."""
        if not items:
            return

        cache_key = f"work_items:{source_name}"
        data = self._serialize_work_items(items, source_name)
        await self._cache.set(
            cache_key=cache_key,
            data=data,
            ttl_seconds=self._work_item_ttl,
            data_type="work_items",
            source=source_name,
        )

    def _serialize_work_items(
        self, items: list[PieceOfWork], source_name: str
    ) -> list[dict[str, Any]]:
        """Serialize work items for caching."""
        from pydantic import BaseModel

        data: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, BaseModel):
                data.append(item.model_dump(mode="json", by_alias=True))
            else:
                # Fallback for non-Pydantic items
                data.append(
                    {
                        "adapter_type": source_name,
                        "external_id": getattr(item, "key", getattr(item, "id", "unknown")),
                        "title": getattr(item, "title", getattr(item, "content", "")),
                        "status": getattr(item, "status", "OPEN"),
                    }
                )
        return data

    def _aggregate_work_fetch_results(
        self, results: list[tuple[str, list[PieceOfWork], str | None]]
    ) -> FetchResult[PieceOfWork]:
        """Aggregate fetch results from all work sources."""
        all_items: list[PieceOfWork] = []
        failed_sources: list[str] = []
        errors: dict[str, str] = {}

        for source_name, items, error in results:
            if error:
                failed_sources.append(source_name)
                errors[source_name] = error
            else:
                all_items.extend(items)

        return FetchResult(
            data=all_items,
            fresh=True,
            failed_sources=failed_sources,
            errors=errors,
        )
