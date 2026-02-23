"""Integration test fixtures and configuration."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from collections.abc import Callable
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from monocle.db.connection import DatabaseManager
from monocle.db.work_store import WorkStore
from monocle.models import CodeReview
from monocle.models import JiraPieceOfWork
from monocle.models import TodoistPieceOfWork
from monocle.sources.registry import SourceRegistry
from monocle.ui.app import MonoApp
from tests.support.factories import make_code_review
from tests.support.factories import make_jira_item
from tests.support.factories import make_todoist_item
from tests.support.stubs import StubCodeReviewSource
from tests.support.stubs import StubPieceOfWorkSource


class MockGitLabSource(StubCodeReviewSource):
    """Compatibility wrapper around StubCodeReviewSource for GitLab tests."""

    def __init__(
        self,
        assigned: list[CodeReview] | None = None,
        authored: list[CodeReview] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
        source_type: str = "gitlab",
    ):
        super().__init__(
            source_type=source_type,
            source_icon="🦊" if source_type == "gitlab" else "🐙",
            assigned=assigned or [],
            authored=authored or [],
            available=available,
            authenticated=authenticated,
            fetch_delay=fetch_delay,
            assigned_exception=failure_exception if should_fail else None,
            authored_exception=failure_exception if should_fail else None,
        )


class MockGitHubSource(StubCodeReviewSource):
    """Compatibility wrapper around StubCodeReviewSource for GitHub tests."""

    def __init__(
        self,
        assigned: list[CodeReview] | None = None,
        authored: list[CodeReview] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
        source_type: str = "github",
    ):
        super().__init__(
            source_type=source_type,
            source_icon="🐙",
            assigned=assigned or [],
            authored=authored or [],
            available=available,
            authenticated=authenticated,
            fetch_delay=fetch_delay,
            assigned_exception=failure_exception if should_fail else None,
            authored_exception=failure_exception if should_fail else None,
        )


class MockJiraSource(StubPieceOfWorkSource):
    """Compatibility wrapper around StubPieceOfWorkSource for Jira tests."""

    def __init__(
        self,
        items: list[Any] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
        source_type: str = "jira",
    ):
        super().__init__(
            source_type=source_type,
            source_icon="🔴",
            items=items or [],
            available=available,
            authenticated=authenticated,
            fetch_delay=fetch_delay,
            items_exception=failure_exception if should_fail else None,
        )


class MockTodoistSource(StubPieceOfWorkSource):
    """Compatibility wrapper around StubPieceOfWorkSource for Todoist tests."""

    def __init__(
        self,
        items: list[Any] | None = None,
        available: bool = True,
        authenticated: bool = True,
        should_fail: bool = False,
        failure_exception: Exception | None = None,
        fetch_delay: float = 0.0,
        source_type: str = "todoist",
    ):
        super().__init__(
            source_type=source_type,
            source_icon="📝",
            items=items or [],
            available=available,
            authenticated=authenticated,
            fetch_delay=fetch_delay,
            items_exception=failure_exception if should_fail else None,
        )


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture(autouse=True)
def reset_database_manager() -> Generator[None, None, None]:
    """Reset singleton state before/after each test for deterministic cleanup."""
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


@pytest.fixture
def mock_gitlab_source() -> MockGitLabSource:
    return MockGitLabSource()


@pytest.fixture
def mock_github_source() -> MockGitHubSource:
    return MockGitHubSource()


@pytest.fixture
def mock_jira_source() -> MockJiraSource:
    return MockJiraSource()


@pytest.fixture
def mock_todoist_source() -> MockTodoistSource:
    return MockTodoistSource()


@pytest.fixture
def mock_source_registry(
    mock_gitlab_source: MockGitLabSource,
    mock_github_source: MockGitHubSource,
    mock_jira_source: MockJiraSource,
    mock_todoist_source: MockTodoistSource,
) -> SourceRegistry:
    """Create a registry with deterministic, unique source identities."""
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
    db = DatabaseManager(str(temp_db_path))
    await db.initialize()

    store = WorkStore(
        source_registry=mock_source_registry,
        code_review_ttl=300,
        work_item_ttl=600,
        background_timeout=30,
    )

    app = MonoApp()

    def mock_create_store(config: Any) -> WorkStore:
        return store

    monkeypatch.setattr("monocle.ui.work_store_factory.create_work_store", mock_create_store)

    yield app

    await db.close()
    DatabaseManager.reset_instance()


@pytest.fixture
def mock_webbrowser() -> Generator[MagicMock, None, None]:
    with patch("webbrowser.open") as mock:
        yield mock


@pytest.fixture
def code_review_factory() -> Callable[..., CodeReview]:
    counter = 0

    def factory(
        adapter_type: str = "gitlab",
        state: str = "open",
        draft: bool = False,
        **kwargs: Any,
    ) -> CodeReview:
        nonlocal counter
        counter += 1
        icon = "🦊" if adapter_type == "gitlab" else "🐙"
        review = make_code_review(
            idx=counter,
            adapter_type=adapter_type,
            adapter_icon=icon,
            state=state,
        )
        payload = review.model_dump()
        payload["draft"] = draft
        payload.update(kwargs)
        return CodeReview(**payload)

    return factory


@pytest.fixture
def jira_work_item_factory() -> Callable[..., JiraPieceOfWork]:
    counter = 0

    def factory(**kwargs: Any) -> JiraPieceOfWork:
        nonlocal counter
        counter += 1
        item = make_jira_item(idx=counter)
        payload = item.model_dump()
        payload.update(kwargs)
        return JiraPieceOfWork(**payload)

    return factory


@pytest.fixture
def todoist_task_factory() -> Callable[..., TodoistPieceOfWork]:
    counter = 0

    def factory(**kwargs: Any) -> TodoistPieceOfWork:
        nonlocal counter
        counter += 1
        item = make_todoist_item(idx=counter)
        payload = item.model_dump(by_alias=True)
        payload.update(kwargs)
        return TodoistPieceOfWork(**payload)

    return factory
