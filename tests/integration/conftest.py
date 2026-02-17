"""Integration test fixtures and configuration.

Provides fixtures for full-stack integration tests with mocked database
and data sources. Each test gets isolated resources.
"""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncGenerator, Callable, Generator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from monocli.db.connection import DatabaseManager
from monocli.db.work_store import FetchResult, WorkStore
from monocli.models import CodeReview, JiraPieceOfWork, TodoistPieceOfWork
from monocli.sources.base import CodeReviewSource, PieceOfWorkSource
from monocli.sources.registry import SourceRegistry
from monocli.ui.app import MonoApp


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture(autouse=True)
def reset_database_manager() -> Generator[None, None, None]:
    """Reset the DatabaseManager singleton before each test."""
    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


@pytest.fixture
async def initialized_db(temp_db_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    """Create and initialize a fresh database for testing."""
    db = DatabaseManager(str(temp_db_path))
    await db.initialize()
    yield db
    await db.close()


class MockCodeReviewSource(CodeReviewSource):
    """Mock code review source for testing.

    Allows configuring behavior for each test:
    - assigned_items: Items to return for fetch_assigned
    - authored_items: Items to return for fetch_authored
    - should_fail: If True, raises exception on fetch
    - failure_exception: Exception to raise when should_fail is True
    """

    def __init__(
        self,
        source_type: str,
        assigned: list[CodeReview] | None = None,
        authored: list[CodeReview] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
    ):
        self._source_type = source_type
        self._assigned = assigned or []
        self._authored = authored or []
        self._available = available
        self._authenticated = authenticated
        self._should_fail = should_fail
        self._failure_exception = failure_exception or Exception("Mock fetch failed")
        self._fetch_delay = fetch_delay

    @property
    def source_type(self) -> str:
        return self._source_type

    @property
    def source_icon(self) -> str:
        icons = {"gitlab": "🦊", "github": "🐙"}
        return icons.get(self._source_type, "📦")

    async def is_available(self) -> bool:
        return self._available

    async def check_auth(self) -> bool:
        return self._authenticated

    async def fetch_assigned(self) -> list[CodeReview]:
        if self._fetch_delay > 0:
            await asyncio.sleep(self._fetch_delay)
        if self._should_fail:
            raise self._failure_exception
        return self._assigned

    async def fetch_authored(self) -> list[CodeReview]:
        if self._fetch_delay > 0:
            await asyncio.sleep(self._fetch_delay)
        if self._should_fail:
            raise self._failure_exception
        return self._authored

    async def fetch_pending_review(self) -> list[CodeReview]:
        return []


class MockPieceOfWorkSource(PieceOfWorkSource):
    """Mock piece of work source for testing.

    Similar to MockCodeReviewSource but for work items.
    """

    def __init__(
        self,
        source_type: str,
        items: list[Any] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
    ):
        self._source_type = source_type
        self._items = items or []
        self._available = available
        self._authenticated = authenticated
        self._should_fail = should_fail
        self._failure_exception = failure_exception or Exception("Mock fetch failed")
        self._fetch_delay = fetch_delay

    @property
    def source_type(self) -> str:
        return self._source_type

    @property
    def source_icon(self) -> str:
        icons = {"jira": "🔴", "todoist": "📝"}
        return icons.get(self._source_type, "📦")

    async def is_available(self) -> bool:
        return self._available

    async def check_auth(self) -> bool:
        return self._authenticated

    async def fetch_items(self) -> list[Any]:
        if self._fetch_delay > 0:
            await asyncio.sleep(self._fetch_delay)
        if self._should_fail:
            raise self._failure_exception
        return self._items


class MockGitLabSource(MockCodeReviewSource):
    """Mock GitLab source for testing.

    Pre-configured with source_type="gitlab" and GitLab-specific icon.
    Tests can set _assigned and _authored attributes to provide data.
    """

    def __init__(
        self,
        assigned: list[CodeReview] | None = None,
        authored: list[CodeReview] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
    ):
        super().__init__(
            source_type="gitlab",
            assigned=assigned,
            authored=authored,
            available=available,
            authenticated=authenticated,
            should_fail=should_fail,
            failure_exception=failure_exception,
            fetch_delay=fetch_delay,
        )


class MockGitHubSource(MockCodeReviewSource):
    """Mock GitHub source for testing.

    Pre-configured with source_type="github" and GitHub-specific icon.
    Tests can set _assigned and _authored attributes to provide data.
    """

    def __init__(
        self,
        assigned: list[CodeReview] | None = None,
        authored: list[CodeReview] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
    ):
        super().__init__(
            source_type="github",
            assigned=assigned,
            authored=authored,
            available=available,
            authenticated=authenticated,
            should_fail=should_fail,
            failure_exception=failure_exception,
            fetch_delay=fetch_delay,
        )


class MockJiraSource(MockPieceOfWorkSource):
    """Mock Jira source for testing.

    Pre-configured with source_type="jira" and Jira-specific icon.
    Tests can set _items attribute to provide data.
    """

    def __init__(
        self,
        items: list[Any] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
    ):
        super().__init__(
            source_type="jira",
            items=items,
            available=available,
            authenticated=authenticated,
            should_fail=should_fail,
            failure_exception=failure_exception,
            fetch_delay=fetch_delay,
        )


class MockTodoistSource(MockPieceOfWorkSource):
    """Mock Todoist source for testing.

    Pre-configured with source_type="todoist" and Todoist-specific icon.
    Tests can set _items attribute to provide data.
    """

    def __init__(
        self,
        items: list[Any] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
    ):
        super().__init__(
            source_type="todoist",
            items=items,
            available=available,
            authenticated=authenticated,
            should_fail=should_fail,
            failure_exception=failure_exception,
            fetch_delay=fetch_delay,
        )


@pytest.fixture
def mock_gitlab_source() -> MockGitLabSource:
    """Create an empty mock GitLab source. Tests should populate with data."""
    return MockGitLabSource()


@pytest.fixture
def mock_github_source() -> MockGitHubSource:
    """Create an empty mock GitHub source. Tests should populate with data."""
    return MockGitHubSource()


@pytest.fixture
def mock_jira_source() -> MockJiraSource:
    """Create an empty mock Jira source. Tests should populate with data."""
    return MockJiraSource()


@pytest.fixture
def mock_todoist_source() -> MockTodoistSource:
    """Create an empty mock Todoist source. Tests should populate with data."""
    return MockTodoistSource()


@pytest.fixture
def mock_source_registry(
    mock_gitlab_source: MockGitLabSource,
    mock_github_source: MockGitHubSource,
    mock_jira_source: MockJiraSource,
    mock_todoist_source: MockTodoistSource,
) -> SourceRegistry:
    """Create a registry with all mock sources."""
    registry = SourceRegistry()
    registry.register_code_review_source(mock_gitlab_source)
    registry.register_code_review_source(mock_github_source)
    registry.register_piece_of_work_source(mock_jira_source)
    registry.register_piece_of_work_source(mock_todoist_source)
    return registry


@pytest.fixture
async def mock_work_store(
    temp_db_path: Path,
    mock_source_registry: SourceRegistry,
) -> AsyncGenerator[WorkStore, None]:
    """Create a WorkStore with mocked sources and fresh database."""
    # Ensure database is initialized
    db = DatabaseManager(str(temp_db_path))
    await db.initialize()

    store = WorkStore(
        source_registry=mock_source_registry,
        code_review_ttl=300,
        work_item_ttl=600,
        background_timeout=30,
    )

    yield store

    await db.close()
    DatabaseManager.reset_instance()


@pytest.fixture
async def app_with_mocked_store(
    temp_db_path: Path,
    mock_source_registry: SourceRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[MonoApp, None]:
    """Create a MonoApp with injected mock WorkStore."""
    # Initialize database
    db = DatabaseManager(str(temp_db_path))
    await db.initialize()

    # Create WorkStore
    store = WorkStore(
        source_registry=mock_source_registry,
        code_review_ttl=300,
        work_item_ttl=600,
        background_timeout=30,
    )

    app = MonoApp()

    # Patch the work store factory to return our mock
    def mock_create_store(config: Any) -> WorkStore:
        return store

    monkeypatch.setattr(
        "monocli.ui.work_store_factory.create_work_store",
        mock_create_store,
    )

    yield app

    await db.close()
    DatabaseManager.reset_instance()


@pytest.fixture
def mock_webbrowser() -> Generator[MagicMock, None, None]:
    """Mock webbrowser.open for testing."""
    with patch("webbrowser.open") as mock:
        yield mock


@pytest.fixture
def code_review_factory() -> Callable[..., CodeReview]:
    """Factory for creating CodeReview objects."""
    counter = 0

    def factory(
        adapter_type: str = "gitlab",
        state: str = "open",
        draft: bool = False,
        **kwargs: Any,
    ) -> CodeReview:
        nonlocal counter
        counter += 1

        defaults = {
            "id": f"cr-{counter}",
            "key": f"!{counter}" if adapter_type == "gitlab" else f"#{counter}",
            "title": f"Test Code Review {counter}",
            "state": state,
            "author": "testuser",
            "source_branch": f"feature/test-{counter}",
            "url": f"https://example.com/{adapter_type}/pr/{counter}",
            "created_at": datetime.now(),
            "draft": draft,
            "adapter_type": adapter_type,
            "adapter_icon": "🦊" if adapter_type == "gitlab" else "🐙",
        }
        defaults.update(kwargs)
        return CodeReview(**defaults)

    return factory


@pytest.fixture
def jira_work_item_factory() -> Callable[..., JiraPieceOfWork]:
    """Factory for creating JiraPieceOfWork objects."""
    counter = 0

    def factory(
        status: str = "Open",
        priority: str = "Medium",
        **kwargs: Any,
    ) -> JiraPieceOfWork:
        nonlocal counter
        counter += 1

        defaults = {
            "key": f"PROJ-{100 + counter}",
            "fields": {
                "summary": f"Test Issue {counter}",
                "status": {"name": status},
                "priority": {"name": priority},
                "assignee": {"displayName": "Test User"},
            },
            "self": f"https://jira.example.com/rest/api/2/issue/{10000 + counter}",
        }
        defaults.update(kwargs)
        return JiraPieceOfWork(**defaults)

    return factory


@pytest.fixture
def todoist_task_factory() -> Callable[..., TodoistPieceOfWork]:
    """Factory for creating TodoistPieceOfWork objects."""
    counter = 0

    def factory(
        priority: int = 1,
        is_completed: bool = False,
        **kwargs: Any,
    ) -> TodoistPieceOfWork:
        nonlocal counter
        counter += 1

        defaults = {
            "id": f"{100000 + counter}",
            "content": f"Test Task {counter}",
            "priority": priority,
            "due": None,
            "project_id": "123",
            "project_name": "Test Project",
            "url": f"https://todoist.com/showTask?id={100000 + counter}",
            "is_completed": is_completed,
        }
        defaults.update(kwargs)
        return TodoistPieceOfWork(**defaults)

    return factory


@pytest.fixture
def async_timeout() -> Callable[[float], Any]:
    """Provide async timeout context manager."""

    def timeout(seconds: float):
        return asyncio.timeout(seconds)

    return timeout
