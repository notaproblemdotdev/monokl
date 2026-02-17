"""Snapshot tests for UI components.

Uses pytest-textual-snapshot to capture visual state of sections.
Run with: pytest --snapshot-update to generate baseline snapshots.
"""

from __future__ import annotations

import pytest

from monocli.db.connection import DatabaseManager
from monocli.db.work_store import WorkStore
from monocli.models import CodeReview, JiraPieceOfWork, TodoistPieceOfWork
from monocli.sources.registry import SourceRegistry
from monocli.ui.app import MonoApp
from tests.integration.conftest import (
    MockGitLabSource,
    MockGitHubSource,
    MockJiraSource,
    MockTodoistSource,
)


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.snapshot
async def test_code_review_section_populated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    snapshot,
) -> None:
    """Snapshot test for code review section with data."""
    # Setup
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    # Create source with data
    source = MockGitLabSource(
        source_type="gitlab",
        assigned=[
            CodeReview(
                id="1",
                key="!42",
                title="Fix authentication bug",
                state="open",
                author="developer",
                source_branch="feature/auth-fix",
                url="https://gitlab.com/test/42",
                adapter_type="gitlab",
                adapter_icon="🦊",
            ),
            CodeReview(
                id="2",
                key="!43",
                title="Update documentation",
                state="open",
                author="writer",
                source_branch="docs/update",
                url="https://gitlab.com/test/43",
                adapter_type="gitlab",
                adapter_icon="🦊",
            ),
        ],
    )

    registry = SourceRegistry()
    registry.register_code_review_source(source)

    store = WorkStore(registry)

    # Create app
    app = MonoApp()

    async def mock_create_store(config):
        return store

    monkeypatch.setattr(
        "monocli.ui.work_store_factory.create_work_store",
        mock_create_store,
    )

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.pause(0.3)

        # Take snapshot of the code review section
        mr_container = pilot.app.query_one("#mr-container")
        assert snapshot == mr_container

    await db.close()


@pytest.mark.snapshot
async def test_piece_of_work_section_populated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    snapshot,
) -> None:
    """Snapshot test for work items section with data."""
    # Setup
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    # Create source with data
    jira_source = MockJiraSource(
        source_type="jira",
        items=[
            JiraPieceOfWork(
                key="PROJ-123",
                fields={
                    "summary": "Implement feature",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "Developer"},
                },
                self="https://jira.example.com/rest/api/2/issue/123",
            ),
        ],
    )

    registry = SourceRegistry()
    registry.register_piece_of_work_source(jira_source)

    store = WorkStore(registry)

    # Create app
    app = MonoApp()

    async def mock_create_store(config):
        return store

    monkeypatch.setattr(
        "monocli.ui.work_store_factory.create_work_store",
        mock_create_store,
    )

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.pause(0.3)

        # Take snapshot of the work section
        work_container = pilot.app.query_one("#work-container")
        assert snapshot == work_container

    await db.close()


@pytest.mark.snapshot
async def test_empty_state_visual(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    snapshot,
) -> None:
    """Snapshot test for empty state."""
    # Setup
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    # Create empty source
    source = MockGitLabSource(
        source_type="gitlab",
        assigned=[],
        authored=[],
    )

    registry = SourceRegistry()
    registry.register_code_review_source(source)

    store = WorkStore(registry)

    # Create app
    app = MonoApp()

    async def mock_create_store(config):
        return store

    monkeypatch.setattr(
        "monocli.ui.work_store_factory.create_work_store",
        mock_create_store,
    )

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.pause(0.3)

        # Take snapshot showing empty state
        mr_container = pilot.app.query_one("#mr-container")
        assert snapshot == mr_container

    await db.close()


@pytest.mark.snapshot
async def test_error_state_visual(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    snapshot,
) -> None:
    """Snapshot test for error state."""
    # Setup
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    # Create failing source
    source = MockGitLabSource(
        source_type="gitlab",
        should_fail=True,
        failure_exception=Exception("Connection failed"),
    )

    registry = SourceRegistry()
    registry.register_code_review_source(source)

    store = WorkStore(registry)

    # Create app
    app = MonoApp()

    async def mock_create_store(config):
        return store

    monkeypatch.setattr(
        "monocli.ui.work_store_factory.create_work_store",
        mock_create_store,
    )

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.pause(0.3)

        # Take snapshot showing error state
        mr_container = pilot.app.query_one("#mr-container")
        assert snapshot == mr_container

    await db.close()


@pytest.mark.snapshot
async def test_full_dashboard_view(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    snapshot,
) -> None:
    """Snapshot test of full dashboard with all sections."""
    # Setup
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    # Create sources with data
    gitlab_source = MockGitLabSource(
        source_type="gitlab",
        assigned=[
            CodeReview(
                id="gl-1",
                key="!42",
                title="Fix authentication bug",
                state="open",
                author="developer1",
                source_branch="feature/auth-fix",
                url="https://gitlab.com/test/42",
                adapter_type="gitlab",
                adapter_icon="🦊",
            ),
        ],
        authored=[
            CodeReview(
                id="gl-2",
                key="!43",
                title="[WIP] New feature",
                state="open",
                author="me",
                source_branch="feature/new",
                url="https://gitlab.com/test/43",
                adapter_type="gitlab",
                adapter_icon="🦊",
            ),
        ],
    )

    jira_source = MockJiraSource(
        source_type="jira",
        items=[
            JiraPieceOfWork(
                key="PROJ-123",
                fields={
                    "summary": "Implement user auth",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "Developer"},
                },
                self="https://jira.example.com/rest/api/2/issue/123",
            ),
            JiraPieceOfWork(
                key="PROJ-124",
                fields={
                    "summary": "Fix bug",
                    "status": {"name": "Open"},
                    "priority": {"name": "Highest"},
                    "assignee": {"displayName": "Developer"},
                },
                self="https://jira.example.com/rest/api/2/issue/124",
            ),
        ],
    )

    todoist_source = MockJiraSource(
        source_type="todoist",
        items=[
            TodoistPieceOfWork(
                id="1",
                content="Review PRs",
                priority=4,
                project_id="123",
                project_name="Work",
                url="https://todoist.com/1",
                is_completed=False,
            ),
        ],
    )

    registry = SourceRegistry()
    registry.register_code_review_source(gitlab_source)
    registry.register_piece_of_work_source(jira_source)
    registry.register_piece_of_work_source(todoist_source)

    store = WorkStore(registry)

    # Create app
    app = MonoApp()

    async def mock_create_store(config):
        return store

    monkeypatch.setattr(
        "monocli.ui.work_store_factory.create_work_store",
        mock_create_store,
    )

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.pause(0.3)

        # Take snapshot of full screen
        screen = pilot.app.screen
        assert snapshot == screen

    await db.close()


@pytest.mark.snapshot
async def test_loading_state_visual(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    snapshot,
) -> None:
    """Snapshot test for loading state."""
    # Setup
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    # Create source with delay
    source = MockGitLabSource(
        source_type="gitlab",
        assigned=[],
        fetch_delay=5.0,  # Long delay to keep loading state
    )

    registry = SourceRegistry()
    registry.register_code_review_source(source)

    store = WorkStore(registry)

    # Create app
    app = MonoApp()

    async def mock_create_store(config):
        return store

    monkeypatch.setattr(
        "monocli.ui.work_store_factory.create_work_store",
        mock_create_store,
    )

    async with app.run_test(size=(120, 40)) as pilot:
        # Check immediately (should be loading)
        await pilot.pause()

        # Take snapshot of loading state
        mr_container = pilot.app.query_one("#mr-container")
        assert snapshot == mr_container

    await db.close()


@pytest.mark.snapshot
async def test_work_section_active_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    snapshot,
) -> None:
    """Snapshot test for work section when active."""
    # Setup
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    # Create sources
    jira_source = MockJiraSource(
        source_type="jira",
        items=[
            JiraPieceOfWork(
                key="PROJ-123",
                fields={
                    "summary": "Test issue",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "Medium"},
                    "assignee": {"displayName": "User"},
                },
                self="https://jira.example.com/rest/api/2/issue/123",
            ),
        ],
    )

    registry = SourceRegistry()
    registry.register_piece_of_work_source(jira_source)

    store = WorkStore(registry)

    # Create app
    app = MonoApp()

    async def mock_create_store(config):
        return store

    monkeypatch.setattr(
        "monocli.ui.work_store_factory.create_work_store",
        mock_create_store,
    )

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.pause(0.3)

        # Switch to work section
        await pilot.press("tab")
        await pilot.press("tab")

        # Take snapshot of active work section
        work_container = pilot.app.query_one("#work-container")
        assert snapshot == work_container

    await db.close()
