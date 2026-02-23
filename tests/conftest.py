"""Shared pytest fixtures and configuration."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from monocle.db.connection import DatabaseManager
from monocle.db.work_store import WorkStore
from monocle.sources.registry import SourceRegistry
from monocle.ui.app import MonoApp
from tests.support.stubs import StubCodeReviewSource
from tests.support.stubs import StubPieceOfWorkSource


@pytest.fixture
def event_loop_policy():
    """Return event loop policy for async tests."""
    import asyncio

    return asyncio.get_event_loop_policy()


@pytest.fixture(autouse=True)
def reset_database_manager() -> Generator[None, None, None]:
    """Reset global DatabaseManager singleton around every test."""
    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create temporary db path."""
    return tmp_path / "test.db"


@pytest.fixture
async def initialized_db(temp_db_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    """Initialize and tear down a temporary test database."""
    db = DatabaseManager(str(temp_db_path))
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def stub_gitlab_source() -> StubCodeReviewSource:
    return StubCodeReviewSource(source_type="gitlab", source_icon="🦊")


@pytest.fixture
def stub_github_source() -> StubCodeReviewSource:
    return StubCodeReviewSource(source_type="github", source_icon="🐙")


@pytest.fixture
def stub_jira_source() -> StubPieceOfWorkSource:
    return StubPieceOfWorkSource(source_type="jira", source_icon="🔴")


@pytest.fixture
def stub_todoist_source() -> StubPieceOfWorkSource:
    return StubPieceOfWorkSource(source_type="todoist", source_icon="📝")


@pytest.fixture
def stub_source_registry(
    stub_gitlab_source: StubCodeReviewSource,
    stub_github_source: StubCodeReviewSource,
    stub_jira_source: StubPieceOfWorkSource,
    stub_todoist_source: StubPieceOfWorkSource,
) -> SourceRegistry:
    registry = SourceRegistry()
    registry.register_code_review_source(stub_gitlab_source)
    registry.register_code_review_source(stub_github_source)
    registry.register_piece_of_work_source(stub_jira_source)
    registry.register_piece_of_work_source(stub_todoist_source)
    return registry


@pytest.fixture
async def stub_work_store(
    temp_db_path: Path,
    stub_source_registry: SourceRegistry,
) -> AsyncGenerator[WorkStore, None]:
    db = DatabaseManager(str(temp_db_path))
    await db.initialize()

    store = WorkStore(source_registry=stub_source_registry, code_review_ttl=300, work_item_ttl=600)
    yield store

    await db.close()
    DatabaseManager.reset_instance()


@pytest.fixture
async def app_with_stub_store(
    monkeypatch: pytest.MonkeyPatch,
    stub_work_store: WorkStore,
) -> AsyncGenerator[MonoApp, None]:
    """Return app configured with stub-backed WorkStore."""
    app = MonoApp()

    def mock_create_store(config: Any) -> WorkStore:
        return stub_work_store

    monkeypatch.setattr("monocle.ui.work_store_factory.create_work_store", mock_create_store)
    return app
