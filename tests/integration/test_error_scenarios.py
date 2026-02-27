"""Integration tests for failure and recovery behavior."""

from __future__ import annotations

import pytest

from monokl.ui.sections import SectionState
from tests.support.factories import make_cli_auth_error
from tests.support.factories import make_code_review
from tests.support.factories import make_todoist_item

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.integration_full
async def test_partial_timeout_one_source_succeeds(temp_db_path, reset_database_manager) -> None:
    """A failing source should not prevent successful sources from returning data."""
    from monokl.db.connection import DatabaseManager
    from monokl.db.work_store import WorkStore
    from monokl.sources.registry import SourceRegistry
    from tests.integration.conftest import MockGitHubSource
    from tests.integration.conftest import MockGitLabSource

    gitlab_source = MockGitLabSource(
        should_fail=True,
        failure_exception=TimeoutError("GitLab fetch timed out"),
        source_type="gitlab",
    )
    github_source = MockGitHubSource(
        assigned=[make_code_review(idx=1, adapter_type="github", adapter_icon="🐙")],
    )

    db = DatabaseManager(str(temp_db_path))
    await db.initialize()

    registry = SourceRegistry()
    registry.register_code_review_source(gitlab_source)
    registry.register_code_review_source(github_source)

    store = WorkStore(registry)
    result = await store.get_code_reviews("assigned", force_refresh=True)

    assert len(result.data) == 1
    assert result.data[0].adapter_type == "github"
    assert "gitlab" in result.failed_sources
    assert "failed to fetch assigned" in result.errors["gitlab"].lower()

    await db.close()


@pytest.mark.integration_full
async def test_auth_failure_display_in_ui(monkeypatch, temp_db_path) -> None:
    """Auth failures should be tracked and leave section in non-data state."""
    from monokl.db.connection import DatabaseManager
    from monokl.db.work_store import WorkStore
    from monokl.sources.registry import SourceRegistry
    from monokl.ui.app import MonoApp
    from tests.integration.conftest import MockGitLabSource

    auth_fail_source = MockGitLabSource(
        should_fail=True,
        failure_exception=make_cli_auth_error(stderr="Please run 'glab auth login'"),
    )

    db = DatabaseManager(str(temp_db_path))
    await db.initialize()

    registry = SourceRegistry()
    registry.register_code_review_source(auth_fail_source)
    store = WorkStore(registry)

    app = MonoApp()

    def mock_create_store(config):
        return store

    monkeypatch.setattr("monokl.ui.work_store_factory.create_work_store", mock_create_store)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        screen = pilot.app.screen
        assert screen.code_review_section.assigned_to_me_section.state in {
            SectionState.EMPTY,
            SectionState.ERROR,
        }
        assert "gitlab" in screen._source_errors

    await db.close()


@pytest.mark.integration_full
async def test_work_item_partial_failure(temp_db_path, reset_database_manager) -> None:
    """A failing work source should still return successful items from another source."""
    from monokl.db.connection import DatabaseManager
    from monokl.db.work_store import WorkStore
    from monokl.sources.registry import SourceRegistry
    from tests.integration.conftest import MockJiraSource
    from tests.integration.conftest import MockTodoistSource

    jira_source = MockJiraSource(
        should_fail=True,
        failure_exception=TimeoutError("Jira API timeout"),
    )
    todoist_source = MockTodoistSource(items=[make_todoist_item(idx=1)])

    db = DatabaseManager(str(temp_db_path))
    await db.initialize()

    registry = SourceRegistry()
    registry.register_piece_of_work_source(jira_source)
    registry.register_piece_of_work_source(todoist_source)

    store = WorkStore(registry)
    result = await store.get_work_items(force_refresh=True)

    assert len(result.data) == 1
    assert "jira" in result.failed_sources
    assert "todoist" not in result.failed_sources

    await db.close()


@pytest.mark.integration_smoke
async def test_error_recovery_on_retry(mock_work_store, mock_gitlab_source) -> None:
    """Source should recover from error after refresh."""
    mock_gitlab_source.assigned_exception = TimeoutError("Temporary failure")

    failed = await mock_work_store.get_code_reviews("assigned", force_refresh=True)
    assert failed.data == []
    assert "gitlab" in failed.failed_sources

    mock_gitlab_source.assigned_exception = None
    mock_gitlab_source.assigned = [
        make_code_review(idx=3, adapter_type="gitlab", adapter_icon="🦊")
    ]

    recovered = await mock_work_store.get_code_reviews("assigned", force_refresh=True)
    assert len(recovered.data) == 1
    assert "gitlab" not in recovered.failed_sources
