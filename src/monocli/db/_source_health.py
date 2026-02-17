"""Source health tracking for WorkStore.

Tracks source failures and prioritizes retries.
This is an internal module - use WorkStore for public API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from dataclasses import field
from typing import ClassVar

from monocli import get_logger

logger = get_logger(__name__)


@dataclass
class _FailureRecord:
    """Record of a source failure."""

    source: str
    error: str
    timestamp: float = field(default_factory=time.time)
    failure_count: int = 1


class _SourceHealth:
    """Track source health for prioritization.

    Records source failures and determines retry priority.
    Failed sources are prioritized for retry to quickly detect recovery.

    Args:
        base_retry_delay: Base delay in seconds before retrying a failed source.
        max_retry_delay: Maximum delay in seconds between retries.
    """

    # Exponential backoff multiplier
    BACKOFF_MULTIPLIER: ClassVar[int] = 2
    # Failure records expire after this many seconds
    RECORD_EXPIRY_SECONDS: ClassVar[int] = 3600  # 1 hour

    def __init__(
        self,
        base_retry_delay: int = 30,
        max_retry_delay: int = 300,  # 5 minutes
    ) -> None:
        self._base_retry_delay = base_retry_delay
        self._max_retry_delay = max_retry_delay
        self._failures: dict[str, _FailureRecord] = {}

    def record_failure(self, source: str, error: str) -> None:
        """Record a failed fetch attempt.

        Args:
            source: Source name that failed.
            error: Error message.
        """
        now = time.time()

        if source in self._failures:
            record = self._failures[source]
            record.failure_count += 1
            record.timestamp = now
            record.error = error
            logger.warning(
                "Source failed again",
                source=source,
                count=record.failure_count,
                error=error,
            )
        else:
            self._failures[source] = _FailureRecord(
                source=source,
                error=error,
                timestamp=now,
                failure_count=1,
            )
            logger.warning("Source failed", source=source, error=error)

    def record_success(self, source: str) -> None:
        """Record a successful fetch.

        Clears any failure records for the source.

        Args:
            source: Source name that succeeded.
        """
        if source in self._failures:
            record = self._failures.pop(source)
            logger.info(
                "Source recovered",
                source=source,
                previous_failures=record.failure_count,
            )

    def get_priority_sources(self, sources: list[str]) -> list[str]:
        """Sort sources by priority for fetching.

        Failed sources come first so we can quickly detect recovery.

        Args:
            sources: List of source names.

        Returns:
            Sorted list with failed sources first.
        """
        self._cleanup_expired()

        def sort_key(source: str) -> tuple:
            if source not in self._failures:
                return (1, 0)  # Healthy sources last
            record = self._failures[source]
            # Failed sources first, ordered by failure count (higher = earlier)
            return (0, -record.failure_count)

        return sorted(sources, key=sort_key)

    def should_retry(self, source: str) -> bool:
        """Check if enough time has passed to retry a failed source.

        Args:
            source: Source name to check.

        Returns:
            True if source should be retried, False otherwise.
        """
        self._cleanup_expired()

        if source not in self._failures:
            return True  # Never failed, can retry

        record = self._failures[source]
        delay = self._calculate_retry_delay(record.failure_count)
        elapsed = time.time() - record.timestamp

        return elapsed >= delay

    def get_retry_delay(self, source: str) -> int:
        """Get seconds to wait before retrying.

        Args:
            source: Source name.

        Returns:
            Seconds to wait, or 0 if source can be retried now.
        """
        if source not in self._failures:
            return 0

        record = self._failures[source]
        delay = self._calculate_retry_delay(record.failure_count)
        elapsed = time.time() - record.timestamp
        remaining = max(0, delay - elapsed)

        return int(remaining)

    def get_failed_sources(self) -> list[str]:
        """Get list of currently failed sources.

        Returns:
            List of source names with active failures.
        """
        self._cleanup_expired()
        return list(self._failures.keys())

    def get_failure_info(self, source: str) -> dict[str, object] | None:
        """Get failure information for a source.

        Args:
            source: Source name.

        Returns:
            Dict with failure info, or None if source is healthy.
        """
        if source not in self._failures:
            return None

        record = self._failures[source]
        return {
            "source": source,
            "error": record.error,
            "failure_count": record.failure_count,
            "last_failure": record.timestamp,
            "retry_delay": self.get_retry_delay(source),
        }

    def _calculate_retry_delay(self, failure_count: int) -> int:
        """Calculate retry delay with exponential backoff."""
        delay = self._base_retry_delay * (self.BACKOFF_MULTIPLIER ** (failure_count - 1))
        return min(delay, self._max_retry_delay)

    def _cleanup_expired(self) -> None:
        """Remove expired failure records."""
        now = time.time()
        expired = [
            source
            for source, record in self._failures.items()
            if now - record.timestamp > self.RECORD_EXPIRY_SECONDS
        ]
        for source in expired:
            del self._failures[source]
            logger.debug("Expired failure record for source", source=source)
