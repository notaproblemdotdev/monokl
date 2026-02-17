"""Internal cache backend operations for WorkStore.

Provides low-level cache operations with TTL support.
This is an internal module - use WorkStore for public API.
"""

from __future__ import annotations

import json
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from monocli import get_logger
from monocli.db.connection import get_db_manager

if TYPE_CHECKING:
    import aiosqlite

logger = get_logger(__name__)

# Default cleanup threshold in days
DEFAULT_CLEANUP_DAYS = 30


class _CacheBackend:
    """Internal cache backend with TTL support.

    Provides low-level cache operations. Not intended for direct use.
    Use WorkStore for high-level data access.

    Args:
        cleanup_days: Days before stale records are cleaned up.
    """

    def __init__(self, cleanup_days: int = DEFAULT_CLEANUP_DAYS) -> None:
        self._cleanup_days = cleanup_days

    async def get(
        self,
        cache_key: str,
        accept_stale: bool = False,
    ) -> list[dict[str, Any]] | None:
        """Get cached data if not expired.

        Args:
            cache_key: Unique cache key.
            accept_stale: If True, return stale data for offline mode.

        Returns:
            List of deserialized JSON objects, or None if cache miss.
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            is_valid = await self._is_cache_valid(conn, cache_key)

            if not is_valid and not accept_stale:
                logger.debug("Cache expired", cache_key=cache_key)
                return None

            cursor = await conn.execute(
                "SELECT raw_json FROM cached_data WHERE cache_key = ?",
                (cache_key,),
            )
            row = await cursor.fetchone()

            if row is None:
                logger.debug("Cache miss", cache_key=cache_key)
                return None

            # Parse JSON - stored as a list of items
            try:
                data = json.loads(row[0])
                if not isinstance(data, list):
                    logger.warning("Cached data is not a list", cache_key=cache_key)
                    return None

                cache_status = "stale" if not is_valid else "fresh"
                logger.debug(
                    "Cache hit",
                    cache_key=cache_key,
                    count=len(data),
                    status=cache_status,
                )
                return data
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse cached data", cache_key=cache_key, error=str(e))
                return None

        except Exception as e:
            logger.error("Failed to get cached data", cache_key=cache_key, error=str(e))
            return None

    async def set(
        self,
        cache_key: str,
        data: list[dict[str, Any]],
        ttl_seconds: int,
        data_type: str,
        source: str,
        subsection: str | None = None,
    ) -> None:
        """Store data in cache.

        Args:
            cache_key: Unique cache key.
            data: List of serializable objects to cache.
            ttl_seconds: Time-to-live in seconds.
            data_type: Type of data (e.g., "code_reviews", "work_items").
            source: Source name (e.g., "gitlab", "jira").
            subsection: Optional subsection (e.g., "assigned", "opened").
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            # Delete existing record
            await conn.execute(
                "DELETE FROM cached_data WHERE cache_key = ?",
                (cache_key,),
            )

            # Serialize data
            raw_json = json.dumps(data)
            cached_at = datetime.now().isoformat()

            # Insert new record
            await conn.execute(
                """
                INSERT INTO cached_data
                (cache_key, data_type, source, subsection, raw_json, cached_at, ttl_seconds, fetch_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (cache_key, data_type, source, subsection, raw_json, cached_at, ttl_seconds),
            )

            logger.debug(
                "Cached data",
                cache_key=cache_key,
                count=len(data),
                ttl=ttl_seconds,
            )

            # Cleanup old records periodically
            await self._cleanup_old_records(conn)

        except Exception as e:
            logger.error("Failed to cache data", cache_key=cache_key, error=str(e))

    async def invalidate(
        self,
        data_type: str | None = None,
        source: str | None = None,
    ) -> None:
        """Invalidate cache entries.

        Args:
            data_type: Filter by data type, or None for all.
            source: Filter by source, or None for all.
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            if data_type is None and source is None:
                # Invalidate all
                await conn.execute("DELETE FROM cached_data")
                logger.info("Invalidated all caches")
            elif data_type is not None and source is not None:
                # Specific data type + source
                await conn.execute(
                    "DELETE FROM cached_data WHERE data_type = ? AND source = ?",
                    (data_type, source),
                )
                logger.info("Invalidated cache", data_type=data_type, source=source)
            elif data_type is not None:
                # All sources for this data type
                await conn.execute(
                    "DELETE FROM cached_data WHERE data_type = ?",
                    (data_type,),
                )
                logger.info("Invalidated cache for data type", data_type=data_type)
            else:
                # All data types for this source
                await conn.execute(
                    "DELETE FROM cached_data WHERE source = ?",
                    (source,),
                )
                logger.info("Invalidated cache for source", source=source)

        except Exception as e:
            logger.error(
                "Failed to invalidate cache", data_type=data_type, source=source, error=str(e)
            )

    async def is_fresh(self, cache_key: str) -> bool:
        """Check if cache is still valid based on TTL.

        Args:
            cache_key: Cache key to check.

        Returns:
            True if cache is fresh, False otherwise.
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()
            return await self._is_cache_valid(conn, cache_key)
        except Exception as e:
            logger.error("Failed to check cache freshness", cache_key=cache_key, error=str(e))
            return False

    async def record_error(self, cache_key: str, error: str) -> None:
        """Record an error for a cache key.

        Args:
            cache_key: Cache key that encountered an error.
            error: Error message to record.
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            await conn.execute(
                "UPDATE cached_data SET last_error = ? WHERE cache_key = ?",
                (error, cache_key),
            )
        except Exception as e:
            logger.error("Failed to record cache error", cache_key=cache_key, error=str(e))

    async def get_cache_info(self, cache_key: str) -> dict[str, Any] | None:
        """Get metadata about a cache entry.

        Args:
            cache_key: Cache key to query.

        Returns:
            Dict with cache metadata, or None if not found.
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            cursor = await conn.execute(
                """
                SELECT cached_at, ttl_seconds, fetch_count, last_error, data_type, source
                FROM cached_data WHERE cache_key = ?
                """,
                (cache_key,),
            )
            row = await cursor.fetchone()

            if row is None:
                return None

            cached_at_str, ttl_seconds, fetch_count, last_error, data_type, source = row
            cached_at = datetime.fromisoformat(cached_at_str)
            expires_at = cached_at + timedelta(seconds=ttl_seconds)
            is_valid = datetime.now() < expires_at

            return {
                "cache_key": cache_key,
                "data_type": data_type,
                "source": source,
                "cached_at": cached_at,
                "ttl_seconds": ttl_seconds,
                "expires_at": expires_at,
                "is_valid": is_valid,
                "fetch_count": fetch_count,
                "last_error": last_error,
            }

        except Exception as e:
            logger.error("Failed to get cache info", cache_key=cache_key, error=str(e))
            return None

    async def _is_cache_valid(
        self,
        conn: aiosqlite.Connection,  # type: ignore[name-defined]
        cache_key: str,
    ) -> bool:
        """Internal method to check cache validity."""
        cursor = await conn.execute(
            "SELECT cached_at, ttl_seconds FROM cached_data WHERE cache_key = ?",
            (cache_key,),
        )
        row = await cursor.fetchone()

        if row is None:
            return False

        cached_at_str, ttl_seconds = row
        cached_at = datetime.fromisoformat(cached_at_str)
        expires_at = cached_at + timedelta(seconds=ttl_seconds)
        return datetime.now() < expires_at

    async def _cleanup_old_records(
        self,
        conn: aiosqlite.Connection,  # type: ignore[name-defined]
    ) -> None:
        """Remove records older than cleanup threshold."""
        cutoff = datetime.now() - timedelta(days=self._cleanup_days)
        cutoff_str = cutoff.isoformat()

        cursor = await conn.execute(
            "DELETE FROM cached_data WHERE cached_at < ?",
            (cutoff_str,),
        )

        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Cleaned up old cache records", deleted=deleted)
