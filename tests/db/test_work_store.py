"""Tests for WorkStore data access layer."""

from __future__ import annotations

import pytest

from monokl.db import FetchResult
from monokl.db import WorkStore
from monokl.db.connection import DatabaseManager
from monokl.models import CodeReview
from monokl.models import PieceOfWork
from monokl.sources.base import CodeReviewSource
from monokl.sources.base import PieceOfWorkSource


class MockCodeReviewSource(CodeReviewSource):
    """Mock code review source for testing."""

    def __init__(
        self,
        source_type: str,
        assigned: list[CodeReview] | None = None,
        authored: list[CodeReview] | None = None,
    ):
        self._source_type = source_type
        self._assigned = assigned or []
        self._authored = authored or []

    @property
    def source_type(self) -> str:
        return self._source_type

    async def is_available(self) -> bool:
        return True

    async def check_auth(self) -> bool:
        return True

    async def fetch_assigned(self) -> list[CodeReview]:
        return self._assigned

    async def fetch_authored(self) -> list[CodeReview]:
        return self._authored

    async def fetch_pending_review(self) -> list[CodeReview]:
        return []


class MockPieceOfWorkSource(PieceOfWorkSource):
    """Mock piece of work source for testing."""

    def __init__(self, source_type: str, items: list[PieceOfWork] | None = None):
        self._source_type = source_type
        self._items = items or []

    @property
    def source_type(self) -> str:
        return self._source_type

    async def is_available(self) -> bool:
        return True

    async def check_auth(self) -> bool:
        return True

    async def fetch_items(self) -> list[PieceOfWork]:
        return self._items


@pytest.fixture(autouse=True)
def reset_db_manager():
    """Reset the singleton instance before each test."""
    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


@pytest.fixture
async def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "workstore_test.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()
    yield db
    await db.close()


class TestWorkStore:
    """Test WorkStore operations."""

    @pytest.mark.asyncio
    async def test_fetch_code_reviews(self, tmp_path):
        """Test fetching code reviews."""
        db_path = tmp_path / "test_code_reviews.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        from monokl.sources.registry import SourceRegistry

        registry = SourceRegistry()
        review1 = CodeReview(
            id="1",
            key="MR-1",
            title="Test MR 1",
            state="open",
            author="Test Author",
            url="https://gitlab.com/test/1",
            source_branch="feature/1",
            adapter_type="mock",
            adapter_icon="🧪",
        )
        review2 = CodeReview(
            id="2",
            key="MR-2",
            title="Test MR 2",
            state="open",
            author="Test Author",
            url="https://gitlab.com/test/2",
            source_branch="feature/2",
            adapter_type="mock",
            adapter_icon="🧪",
        )
        registry.register_code_review_source(
            MockCodeReviewSource("mock", assigned=[review1, review2])
        )

        store = WorkStore(registry)

        # Fetch assigned reviews
        result = await store.get_code_reviews("assigned", force_refresh=True)
        assert isinstance(result, FetchResult)
        assert len(result.data) == 2
        assert result.fresh is True
        assert result.failed_sources == []

        await db.close()

    @pytest.mark.asyncio
    async def test_fetch_work_items(self, tmp_path):
        """Test fetching work items."""
        db_path = tmp_path / "test_work_items.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        from monokl.sources.registry import SourceRegistry

        registry = SourceRegistry()
        # Create a mock work item that satisfies PieceOfWork protocol
        from monokl.models import JiraWorkItem

        item1 = JiraWorkItem(
            key="TEST-1",
            title="Test Issue 1",
            status="OPEN",
            url="https://jira.example.com/TEST-1",
            priority="High",
        )
        registry.register_piece_of_work_source(MockPieceOfWorkSource("mock", items=[item1]))

        store = WorkStore(registry)

        # Fetch work items
        result = await store.get_work_items(force_refresh=True)
        assert isinstance(result, FetchResult)
        assert len(result.data) == 1
        assert result.fresh is True

        await db.close()

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, tmp_path):
        """Test cache invalidation."""
        db_path = tmp_path / "test_invalidate.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        from monokl.sources.registry import SourceRegistry

        registry = SourceRegistry()
        registry.register_code_review_source(MockCodeReviewSource("mock"))
        registry.register_piece_of_work_source(MockPieceOfWorkSource("mock"))

        store = WorkStore(registry)

        # Initially should not be fresh
        assert await store.is_fresh("code_reviews") is False
        assert await store.is_fresh("work_items") is False

        # Fetch to populate cache
        await store.get_code_reviews("assigned", force_refresh=True)
        await store.get_work_items(force_refresh=True)

        # Now should be fresh
        assert await store.is_fresh("code_reviews") is True
        assert await store.is_fresh("work_items") is True

        # Invalidate code reviews
        await store.invalidate(data_type="code_reviews")
        assert await store.is_fresh("code_reviews") is False
        # Work items should still be fresh
        assert await store.is_fresh("work_items") is True

        # Invalidate all
        await store.invalidate()
        assert await store.is_fresh("work_items") is False

        await db.close()

    @pytest.mark.asyncio
    async def test_partial_failure(self, tmp_path):
        """Test handling of partial source failures."""
        db_path = tmp_path / "test_partial_failure.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        from monokl.sources.registry import SourceRegistry

        registry = SourceRegistry()

        # Add a working source
        review1 = CodeReview(
            id="1",
            key="MR-1",
            title="Working MR",
            state="open",
            author="Test",
            url="https://gitlab.com/test/1",
            source_branch="feature",
            adapter_type="working",
            adapter_icon="✅",
        )
        registry.register_code_review_source(MockCodeReviewSource("working", assigned=[review1]))

        # Add a failing source
        class FailingSource(CodeReviewSource):
            @property
            def source_type(self) -> str:
                return "failing"

            async def is_available(self) -> bool:
                return True

            async def check_auth(self) -> bool:
                return True

            async def fetch_assigned(self) -> list[CodeReview]:
                raise Exception("Simulated failure")

            async def fetch_authored(self) -> list[CodeReview]:
                return []

            async def fetch_pending_review(self) -> list[CodeReview]:
                return []

        registry.register_code_review_source(FailingSource())

        store = WorkStore(registry)

        # Fetch should return data from working source but track failure
        result = await store.get_code_reviews("assigned", force_refresh=True)
        assert len(result.data) == 1
        assert result.data[0].title == "Working MR"
        assert "failing" in result.failed_sources
        assert "Simulated failure" in result.errors.get("failing", "")

        await db.close()

    @pytest.mark.asyncio
    async def test_fetch_result_structure(self):
        """Test FetchResult dataclass structure."""
        from monokl.models import CodeReview

        review = CodeReview(
            id="1",
            key="MR-1",
            title="Test",
            state="open",
            author="Test",
            url="https://test.com",
            adapter_type="test",
            adapter_icon="🧪",
        )

        result = FetchResult(
            data=[review],
            fresh=True,
            failed_sources=["source1"],
            errors={"source1": "Error message"},
        )

        assert len(result.data) == 1
        assert result.fresh is True
        assert result.failed_sources == ["source1"]
        assert result.errors == {"source1": "Error message"}
