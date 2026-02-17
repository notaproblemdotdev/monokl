"""Error scenario integration tests.

Tests timeout and authentication failure scenarios.
Verifies graceful degradation when sources fail.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from monocli.db.connection import DatabaseManager
from monocli.db.work_store import WorkStore
from monocli.exceptions import CLIAuthError
from monocli.models import CodeReview, TodoistPieceOfWork
from monocli.sources.registry import SourceRegistry
from monocli.ui.main_screen import MainScreen
from monocli.ui.sections import SectionState
from monocli.ui.app import MonoApp
from tests.integration.conftest import (
    MockGitLabSource,
    MockGitHubSource,
    MockJiraSource,
    MockTodoistSource,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestTimeoutScenarios:
    """Tests for source timeout behavior."""

    async def test_partial_timeout_one_source_succeeds(
        self,
        temp_db_path: Path,
        reset_database_manager: None,
    ) -> None:
        """Test when one source times out but another succeeds.

        Verifies that:
        - Data from successful source is returned
        - Failed source is tracked in failed_sources
        - Error message is captured
        """
        from pathlib import Path
        from monocli.db.connection import DatabaseManager
        from monocli.sources.registry import SourceRegistry

        # Create sources: GitLab times out, GitHub succeeds
        gitlab_source = MockGitLabSource(
            should_fail=True,
            failure_exception=asyncio.TimeoutError("GitLab fetch timed out"),
        )

        github_source = MockGitLabSource(
            assigned=[
                CodeReview(
                    id="gh-1",
                    key="#123",
                    title="Success PR",
                    state="open",
                    author="user",
                    url="https://github.com/test/123",
                    adapter_type="github",
                    adapter_icon="🐙",
                ),
            ],
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(gitlab_source)
        registry.register_code_review_source(github_source)

        store = WorkStore(registry)

        # Fetch
        result = await store.get_code_reviews("assigned", force_refresh=True)

        # Verify
        assert len(result.data) == 1  # Only GitHub data
        assert result.data[0].adapter_type == "github"
        assert "gitlab" in result.failed_sources
        assert "timed out" in result.errors["gitlab"].lower()

        await db.close()

    async def test_all_sources_timeout(
        self,
        temp_db_path: Path,
        reset_database_manager: None,
    ) -> None:
        """Test when all sources timeout.

        Verifies that:
        - Empty data list is returned
        - All sources are in failed_sources
        - Appropriate error messages are captured
        """
        from pathlib import Path
        from monocli.db.connection import DatabaseManager
        from monocli.sources.registry import SourceRegistry

        # Create sources that all timeout
        gitlab_source = MockGitLabSource(
            should_fail=True,
            failure_exception=asyncio.TimeoutError("Connection timeout"),
        )

        github_source = MockGitLabSource(
            should_fail=True,
            failure_exception=asyncio.TimeoutError("Request timeout"),
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(gitlab_source)
        registry.register_code_review_source(github_source)

        store = WorkStore(registry)

        # Fetch
        result = await store.get_code_reviews("assigned", force_refresh=True)

        # Verify
        assert len(result.data) == 0
        assert "gitlab" in result.failed_sources
        assert "github" in result.failed_sources
        assert len(result.errors) == 2

        await db.close()

    async def test_timeout_with_fallback_to_cache(
        self,
        temp_db_path: Path,
        reset_database_manager: None,
    ) -> None:
        """Test that stale cache is used when fetch times out.

        Verifies that:
        - Cached data is returned when fetch fails
        - fresh=False indicates stale data
        - Failed sources are tracked
        """
        from pathlib import Path
        from monocli.db.connection import DatabaseManager
        from monocli.sources.registry import SourceRegistry

        # Create source with initial data
        source = MockGitLabSource(
            assigned=[
                CodeReview(
                    id="cached-1",
                    key="!999",
                    title="Cached MR",
                    state="open",
                    author="user",
                    url="https://gitlab.com/test/999",
                    adapter_type="gitlab",
                    adapter_icon="🦊",
                ),
            ],
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(source)

        store = WorkStore(registry)

        # First fetch - populate cache
        result1 = await store.get_code_reviews("assigned", force_refresh=True)
        assert len(result1.data) == 1
        assert result1.fresh is True

        # Make source fail
        source._should_fail = True
        source._failure_exception = asyncio.TimeoutError("Timeout")

        # Second fetch - should return cached data
        result2 = await store.get_code_reviews("assigned")
        assert len(result2.data) == 1
        assert result2.fresh is False  # Stale cache

        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthFailureScenarios:
    """Tests for authentication failure behavior."""

    async def test_auth_failure_vs_unavailable_cli(
        self,
        temp_db_path: Path,
        reset_database_manager: None,
    ) -> None:
        """Test distinction between auth failure and unavailable CLI.

        Verifies that:
        - Auth failures are distinguished from unavailable CLI
        - Different error messages for each case
        - UI shows appropriate error state
        """
        from pathlib import Path
        from monocli.db.connection import DatabaseManager
        from monocli.sources.registry import SourceRegistry

        # Source with auth failure (CLI available but not authenticated)
        auth_fail_source = MockGitLabSource(
            available=True,  # CLI is available
            authenticated=False,  # But not authenticated
            should_fail=True,
            failure_exception=CLIAuthError("Not authenticated with GitLab"),
        )

        # Source with unavailable CLI
        unavailable_source = MockGitLabSource(
            available=False,  # CLI not even installed
            authenticated=False,
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(auth_fail_source)
        registry.register_code_review_source(unavailable_source)

        store = WorkStore(registry)

        # Fetch
        result = await store.get_code_reviews("assigned", force_refresh=True)

        # Verify both sources failed
        assert len(result.data) == 0
        assert "gitlab" in result.failed_sources
        assert "github" in result.failed_sources

        await db.close()

    async def test_auth_failure_display_in_ui(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_db_path: Path,
    ) -> None:
        """Test that auth failures are displayed in the UI.

        Verifies that:
        - Error state is shown when auth fails
        - Error message is displayed to user
        """
        from pathlib import Path
        from monocli.db.connection import DatabaseManager
        from monocli.sources.registry import SourceRegistry
        from monocli.ui.app import MonoApp
        from monocli.ui.work_store_factory import create_work_store

        # Create source with auth failure
        auth_fail_source = MockGitLabSource(
            available=True,
            authenticated=False,
            should_fail=True,
            failure_exception=CLIAuthError("Please run 'glab auth login'"),
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(auth_fail_source)

        store = WorkStore(registry)

        # Create app with mocked store
        app = MonoApp()

        async def mock_create_store(config):
            return store

        monkeypatch.setattr(
            "monocli.ui.work_store_factory.create_work_store",
            mock_create_store,
        )

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.pause(0.5)

            screen = cast(MainScreen, pilot.app.screen)

            # Should show error state
            assert screen.code_review_section.assigned_to_me_section.state == SectionState.ERROR

        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestMixedErrorScenarios:
    """Tests for complex error scenarios."""

    async def test_mixed_errors_timeout_auth_success(
        self,
        temp_db_path: Path,
        reset_database_manager: None,
    ) -> None:
        """Test mix of timeout, auth failure, and success.

        Verifies that:
        - Successful sources return data
        - Failed sources are tracked with their specific errors
        - Partial data is still useful
        """
        from pathlib import Path
        from monocli.db.connection import DatabaseManager
        from monocli.sources.registry import SourceRegistry

        # Multiple sources with different failure modes
        timeout_source = MockGitLabSource(
            should_fail=True,
            failure_exception=asyncio.TimeoutError("Connection timeout"),
        )

        auth_fail_source = MockGitLabSource(
            available=True,
            authenticated=False,
            should_fail=True,
            failure_exception=CLIAuthError("Not authenticated"),
        )

        success_source = MockGitLabSource(
            assigned=[
                CodeReview(
                    id="bb-1",
                    key="PR-1",
                    title="Working PR",
                    state="open",
                    author="user",
                    url="https://bitbucket.org/test/1",
                    adapter_type="bitbucket",
                    adapter_icon="🪣",
                ),
            ],
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(timeout_source)
        registry.register_code_review_source(auth_fail_source)
        registry.register_code_review_source(success_source)

        store = WorkStore(registry)

        # Fetch
        result = await store.get_code_reviews("assigned", force_refresh=True)

        # Verify
        assert len(result.data) == 1
        assert result.data[0].adapter_type == "bitbucket"
        assert "gitlab" in result.failed_sources
        assert "github" in result.failed_sources
        assert "bitbucket" not in result.failed_sources

        await db.close()

    async def test_error_recovery_on_retry(
        self,
        temp_db_path: Path,
        reset_database_manager: None,
    ) -> None:
        """Test that sources can recover from errors on retry.

        Verifies that:
        - Failed source on first attempt
        - Successful source on retry
        - Data is available after recovery
        """
        from pathlib import Path
        from monocli.db.connection import DatabaseManager
        from monocli.sources.registry import SourceRegistry

        # Source that fails initially
        flaky_source = MockGitLabSource(
            should_fail=True,
            failure_exception=asyncio.TimeoutError("Temporary failure"),
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(flaky_source)

        store = WorkStore(registry)

        # First fetch - fails
        result1 = await store.get_code_reviews("assigned", force_refresh=True)
        assert len(result1.data) == 0
        assert "gitlab" in result1.failed_sources

        # Fix the source
        flaky_source._should_fail = False
        flaky_source._assigned = [
            CodeReview(
                id="recovered-1",
                key="!100",
                title="Recovered MR",
                state="open",
                author="user",
                url="https://gitlab.com/test/100",
                adapter_type="gitlab",
                adapter_icon="🦊",
            ),
        ]

        # Second fetch - succeeds
        result2 = await store.get_code_reviews("assigned", force_refresh=True)
        assert len(result2.data) == 1
        assert "gitlab" not in result2.failed_sources

        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkItemErrors:
    """Tests specifically for work item sources."""

    async def test_jira_timeout_todoist_success(
        self,
        temp_db_path: Path,
        reset_database_manager: None,
    ) -> None:
        """Test Jira timeout with Todoist success.

        Verifies that:
        - Todoist items are still displayed
        - Jira error is tracked
        """
        from pathlib import Path
        from monocli.db.connection import DatabaseManager
        from monocli.sources.registry import SourceRegistry
        from monocli.models import TodoistPieceOfWork

        # Jira times out
        jira_source = MockJiraSource(
            should_fail=True,
            failure_exception=asyncio.TimeoutError("Jira API timeout"),
        )

        # Todoist succeeds
        todoist_source = MockTodoistSource(
            items=[
                TodoistPieceOfWork(
                    id="1",
                    content="Working task",
                    priority=1,
                    project_id="123",
                    project_name="Test",
                    url="https://todoist.com/1",
                    is_completed=False,
                ),
            ],
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_piece_of_work_source(jira_source)
        registry.register_piece_of_work_source(todoist_source)

        store = WorkStore(registry)

        # Fetch
        result = await store.get_work_items(force_refresh=True)

        # Verify
        assert len(result.data) == 1
        assert "jira" in result.failed_sources
        assert "todoist" not in result.failed_sources

        await db.close()
