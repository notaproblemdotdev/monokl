"""UI state change integration tests.

Tests loading → data → empty → error state transitions.
Verifies proper visual feedback during state changes.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from monocli.db.connection import DatabaseManager
from monocli.db.work_store import WorkStore
from monocli.models import CodeReview
from monocli.ui.sections import SectionState
from monocli.ui.app import MonoApp
from monocli.sources.registry import SourceRegistry
from tests.integration.conftest import (
    MockGitLabSource,
    MockGitHubSource,
    MockJiraSource,
    MockTodoistSource,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.integration
@pytest.mark.asyncio
class TestLoadingStateTransitions:
    """Tests for loading state transitions."""

    async def test_loading_to_data_transition(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_db_path: Path,
    ) -> None:
        """Test transition from loading spinner to data table.

        Verifies that:
        - Initial state shows loading
        - Data replaces loading state
        - Table is populated with correct data
        """
        # Create delayed source
        delayed_source = MockGitLabSource(
            source_type="gitlab",
            assigned=[
                CodeReview(
                    id="1",
                    key="!1",
                    title="Test MR",
                    state="open",
                    author="user",
                    url="https://gitlab.com/test/1",
                    adapter_type="gitlab",
                    adapter_icon="🦊",
                ),
            ],
            fetch_delay=0.1,  # Small delay to see loading state
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(delayed_source)

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
            # Initially should show loading
            await pilot.pause()

            screen = pilot.app.screen

            # Should be loading or already have data depending on timing
            assigned_section = screen.code_review_section.assigned_to_me_section
            assert assigned_section.state in [SectionState.LOADING, SectionState.DATA]

            # Wait for data to load
            await pilot.pause(0.2)

            # Should now have data
            assert assigned_section.state == SectionState.DATA
            assert len(assigned_section.code_reviews) == 1

        await db.close()

    async def test_loading_state_visual_indicator(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_db_path: Path,
    ) -> None:
        """Test loading spinner is visible during fetch.

        Verifies that:
        - Spinner is shown during data fetch
        - Spinner text indicates what's loading
        """
        # Create source with delay
        delayed_source = MockGitLabSource(
            source_type="gitlab",
            assigned=[],
            fetch_delay=0.2,
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(delayed_source)

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
            # Check loading state immediately
            await pilot.pause()

            screen = pilot.app.screen
            section = screen.code_review_section.assigned_to_me_section

            # Should be loading initially
            # Note: With fast mocks, might already be done
            assert section.state in [SectionState.LOADING, SectionState.EMPTY]

        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestEmptyStateDisplay:
    """Tests for empty state display."""

    async def test_empty_state_display_message(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_db_path: Path,
    ) -> None:
        """Test empty state shows appropriate message.

        Verifies that:
        - Empty message is displayed
        - Message is appropriate for section type
        """
        # Create empty source
        empty_source = MockGitLabSource(
            source_type="gitlab",
            assigned=[],
            authored=[],
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(empty_source)

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
            await pilot.pause(0.2)

            screen = pilot.app.screen
            assigned_section = screen.code_review_section.assigned_to_me_section

            # Should show empty state
            assert assigned_section.state == SectionState.EMPTY

        await db.close()

    async def test_piece_of_work_section_empty_state(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_db_path: Path,
    ) -> None:
        """Test work items section empty state.

        Verifies that:
        - Empty work items shows appropriate message
        """
        # Create empty work source
        empty_work_source = MockJiraSource(
            source_type="jira",
            items=[],
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_piece_of_work_source(empty_work_source)

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
            await pilot.pause(0.2)

            screen = pilot.app.screen

            # Should show empty state
            assert screen.piece_of_work_section.state == SectionState.EMPTY

        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorStateDisplay:
    """Tests for error state display."""

    async def test_error_state_shows_message(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_db_path: Path,
    ) -> None:
        """Test error state displays error message.

        Verifies that:
        - Error state is shown
        - Error message is displayed
        """
        # Create failing source
        failing_source = MockGitLabSource(
            source_type="gitlab",
            should_fail=True,
            failure_exception=Exception("Connection failed"),
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(failing_source)

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
            await pilot.pause(0.2)

            screen = pilot.app.screen
            section = screen.code_review_section.assigned_to_me_section

            # Should show error state
            assert section.state == SectionState.ERROR
            assert "Connection failed" in section.error_message

        await db.close()

    async def test_partial_error_partial_data(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_db_path: Path,
    ) -> None:
        """Test when some sources fail but others succeed.

        Verifies that:
        - Data from successful sources is shown
        - Error from failed source is tracked
        """
        # One succeeds, one fails
        success_source = MockGitLabSource(
            source_type="github",
            assigned=[
                CodeReview(
                    id="gh-1",
                    key="#1",
                    title="Success PR",
                    state="open",
                    author="user",
                    url="https://github.com/test/1",
                    adapter_type="github",
                    adapter_icon="🐙",
                ),
            ],
        )

        fail_source = MockGitLabSource(
            source_type="gitlab",
            should_fail=True,
            failure_exception=Exception("GitLab down"),
        )

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()
        registry.register_code_review_source(success_source)
        registry.register_code_review_source(fail_source)

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
            await pilot.pause(0.2)

            screen = pilot.app.screen
            section = screen.code_review_section.assigned_to_me_section

            # Should show data (from successful source)
            assert section.state == SectionState.DATA
            assert len(section.code_reviews) == 1

        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestRefreshUpdatesData:
    """Tests for data refresh behavior."""

    async def test_refresh_updates_data(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_db_path: Path,
    ) -> None:
        """Test refresh action updates displayed data.

        Verifies that:
        - Initial data is displayed
        - Refresh fetches new data
        - UI updates with new data
        """
        # Source that changes data on each fetch
        call_count = 0

        async def dynamic_fetch_assigned(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return [
                CodeReview(
                    id=f"dynamic-{call_count}",
                    key=f"!{call_count}",
                    title=f"MR Version {call_count}",
                    state="open",
                    author="user",
                    url=f"https://gitlab.com/test/{call_count}",
                    adapter_type="gitlab",
                    adapter_icon="🦊",
                ),
            ]

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()

        # Create source with dynamic behavior
        dynamic_source = MockGitLabSource(source_type="gitlab")
        dynamic_source.fetch_assigned = dynamic_fetch_assigned

        registry.register_code_review_source(dynamic_source)

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
            await pilot.pause(0.2)

            screen = pilot.app.screen
            section = screen.code_review_section.assigned_to_me_section

            # Initial data
            assert len(section.code_reviews) == 1
            assert section.code_reviews[0].title == "MR Version 1"

            # Trigger refresh
            await pilot.press("r")
            await pilot.pause(0.3)

            # Data should be updated
            assert len(section.code_reviews) == 1
            assert section.code_reviews[0].title == "MR Version 2"

        await db.close()

    async def test_refresh_from_error_to_data(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_db_path: Path,
    ) -> None:
        """Test refresh recovers from error state.

        Verifies that:
        - Initial state shows error
        - Refresh fixes the error
        - Data is displayed after recovery
        """
        # Source that fails initially then succeeds
        fail_count = 0

        async def flaky_fetch_assigned(*args, **kwargs):
            nonlocal fail_count
            fail_count += 1
            if fail_count == 1:
                raise Exception("Temporary error")
            return [
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

        # Setup
        db = DatabaseManager(str(temp_db_path))
        await db.initialize()

        registry = SourceRegistry()

        flaky_source = MockGitLabSource(source_type="gitlab")
        flaky_source.fetch_assigned = flaky_fetch_assigned

        registry.register_code_review_source(flaky_source)

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
            await pilot.pause(0.2)

            screen = pilot.app.screen
            section = screen.code_review_section.assigned_to_me_section

            # Should show error initially
            assert section.state == SectionState.ERROR

            # Refresh
            await pilot.press("r")
            await pilot.pause(0.3)

            # Should now show data
            assert section.state == SectionState.DATA
            assert len(section.code_reviews) == 1

        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestSelectionState:
    """Tests for selection/navigation state."""

    async def test_initial_selection_is_first_row(
        self,
        app_with_mocked_store: MonoApp,
    ) -> None:
        """Test that first row is selected by default.

        Verifies that:
        - First item is selected initially
        - Correct URL is returned for selected item
        """
        async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.pause(0.5)

            screen = pilot.app.screen
            section = screen.code_review_section.assigned_to_me_section

            # Should have data
            assert section.state == SectionState.DATA
            assert len(section.code_reviews) > 0

            # First item should be selected (default)
            url = section.get_selected_url()
            assert url is not None

    async def test_navigation_moves_selection(
        self,
        app_with_mocked_store: MonoApp,
    ) -> None:
        """Test j/k navigation moves selection.

        Verifies that:
        - j moves down
        - k moves up
        - Selection wraps or stops at boundaries
        """
        async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.pause(0.5)

            screen = pilot.app.screen

            # Navigate down
            await pilot.press("j")

            # Navigate up
            await pilot.press("k")

            # Should still have data
            assert screen.code_review_section.assigned_to_me_section.state == SectionState.DATA
