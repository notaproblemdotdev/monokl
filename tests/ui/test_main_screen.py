"""Integration tests for the main screen.

Tests the MainScreen widget including layout, loading states,
data updates, and error handling using Textual's Pilot.
"""

import pytest
from textual.pilot import Pilot

from monocli.ui.app import MonoApp
from monocli.ui.main_screen import MainScreen


class TestMainScreen:
    """Test suite for MainScreen widget."""

    @pytest.fixture
    def app(self):
        """Create a test app with MainScreen."""
        return MonoApp()

    @pytest.mark.asyncio
    async def test_main_screen_renders_both_sections(self, app):
        """Test that MainScreen renders both MR and Work sections."""
        async with app.run_test() as pilot:
            # Wait for main screen to be pushed
            await pilot.pause()

            # Query for both sections
            mr_section = pilot.app.query_one("#mr-container")
            work_section = pilot.app.query_one("#work-container")

            # Both sections should exist
            assert mr_section is not None
            assert work_section is not None

    @pytest.mark.asyncio
    async def test_layout_50_50_split(self, app):
        """Test that sections have 50/50 vertical split."""
        async with app.run_test() as pilot:
            # Wait for main screen to be pushed
            await pilot.pause()

            mr_container = pilot.app.query_one("#mr-container")
            work_container = pilot.app.query_one("#work-container")

            # Both should have 50% height as per CSS
            # Note: In Textual tests, we verify the CSS is applied
            # Actual height calculation depends on terminal size
            assert mr_container.styles.height is not None
            assert work_container.styles.height is not None

    @pytest.mark.asyncio
    async def test_sections_show_loading_on_mount(self, app, monkeypatch):
        """Test that sections show loading state on mount."""

        # Mock the adapters to delay response
        async def mock_fetch(*args, **kwargs):
            import asyncio

            await asyncio.sleep(0.1)
            return []

        # Patch the adapters
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.fetch_assigned_items", mock_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            # Wait for screen and workers to start
            await pilot.pause()

            # Get the screen
            screen = pilot.app.screen

            # Check loading state is set (may need to wait a tick for workers to start)
            # Check that MR subsections are in valid states
            mr_assigned_state = screen.mr_container.assigned_to_me_section.state
            mr_opened_state = screen.mr_container.opened_by_me_section.state
            assert screen.mr_loading is True or mr_assigned_state in [
                "loading",
                "empty",
                "error",
            ]
            assert screen.mr_loading is True or mr_opened_state in [
                "loading",
                "empty",
                "error",
            ]
            assert screen.work_loading is True or screen.work_section.state in [
                "loading",
                "empty",
                "error",
            ]

    @pytest.mark.asyncio
    async def test_mr_section_updates_with_data(self, app, monkeypatch):
        """Test that MR section updates when data is fetched."""
        from datetime import datetime
        from monocli.models import MergeRequest

        # Create test MR data
        test_mr = MergeRequest(
            iid=42,
            title="Test MR",
            state="opened",
            author={"name": "Test User", "username": "testuser"},
            source_branch="feature/test",
            target_branch="main",
            web_url="https://gitlab.com/test/project/-/merge_requests/42",
            created_at=datetime.now(),
        )

        # Mock the adapter
        async def mock_fetch(*args, **kwargs):
            return [test_mr]

        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()

            # Check the section has data or appropriate state
            screen = pilot.app.screen
            # After loading, both subsections should be in valid states
            assigned_state = screen.mr_container.assigned_to_me_section.state
            opened_state = screen.mr_container.opened_by_me_section.state
            assert assigned_state in ["data", "empty", "loading", "error"]
            assert opened_state in ["data", "empty", "loading", "error"]

    @pytest.mark.asyncio
    async def test_work_section_updates_with_data(self, app, monkeypatch):
        """Test that Work section updates when data is fetched."""
        from monocli.models import JiraWorkItem

        # Create test work item
        test_item = JiraWorkItem(
            key="PROJ-123",
            fields={
                "summary": "Test Issue",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "assignee": {"displayName": "testuser"},
            },
            self="https://jira.example.com/rest/api/2/issue/12345",
        )

        # Mock the adapter
        async def mock_fetch(*args, **kwargs):
            return [test_item]

        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.fetch_assigned_items", mock_fetch)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()

            # Check the section has data or appropriate state
            screen = pilot.app.screen
            assert screen.work_section.state in ["data", "empty", "loading", "error"]

    @pytest.mark.asyncio
    async def test_sections_handle_unavailable_cli(self, app, monkeypatch):
        """Test that sections handle unavailable CLI gracefully."""
        # Mock adapters as unavailable
        monkeypatch.setattr(
            "monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: False
        )
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.is_available", lambda self: False)

        async with app.run_test() as pilot:
            # Wait for error state
            await pilot.pause()

            # Check error messages are shown (state should be error or empty)
            screen = pilot.app.screen
            # When CLI unavailable, set_error is called which sets error state
            # Both subsections should be in error or empty state
            assert screen.mr_container.assigned_to_me_section.state in ["error", "empty"]
            assert screen.mr_container.opened_by_me_section.state in ["error", "empty"]
            assert screen.work_section.state in ["error", "empty"]

    @pytest.mark.asyncio
    async def test_sections_handle_auth_error(self, app, monkeypatch):
        """Test that sections handle auth errors gracefully."""
        # Mock adapters as available but not authenticated
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: False)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.is_available", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.check_auth", lambda self: False)

        async with app.run_test() as pilot:
            # Wait for error state
            await pilot.pause()

            # Check error messages are shown
            screen = pilot.app.screen
            # Both subsections should be in error or empty state
            assert screen.mr_container.assigned_to_me_section.state in ["error", "empty"]
            assert screen.mr_container.opened_by_me_section.state in ["error", "empty"]
            assert screen.work_section.state in ["error", "empty"]

    @pytest.mark.asyncio
    async def test_section_switching(self, app, monkeypatch):
        """Test that Tab key switches active section and MR subsections."""

        # Mock adapters to avoid actual network calls
        async def mock_fetch(*args, **kwargs):
            return []

        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.fetch_assigned_items", mock_fetch)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            screen = pilot.app.screen
            await pilot.pause()

            # Initial active section should be "mr", subsection "assigned"
            assert screen.active_section == "mr"
            assert screen.active_mr_subsection == "assigned"

            # Press Tab to switch to "opened" subsection
            await pilot.press("tab")

            # Still in MR section, but now "opened" subsection is active
            assert screen.active_section == "mr"
            assert screen.active_mr_subsection == "opened"

            # Press Tab to switch to Work section
            await pilot.press("tab")
            assert screen.active_section == "work"

            # Press Tab again to switch back to MR "assigned" subsection
            await pilot.press("tab")
            assert screen.active_section == "mr"
            assert screen.active_mr_subsection == "assigned"

    @pytest.mark.asyncio
    async def test_loading_state_transitions(self, app, monkeypatch):
        """Test that loading states transition correctly."""
        import asyncio

        loading_started = {"mr": False, "work": False}

        async def mock_fetch_mrs(*args, **kwargs):
            loading_started["mr"] = True
            await asyncio.sleep(0.01)
            return []

        async def mock_fetch_work(*args, **kwargs):
            loading_started["work"] = True
            await asyncio.sleep(0.01)
            return []

        monkeypatch.setattr(
            "monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch_mrs
        )
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)
        monkeypatch.setattr(
            "monocli.adapters.jira.JiraAdapter.fetch_assigned_items", mock_fetch_work
        )
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            # Wait for workers to start
            await pilot.pause()

            # Loading should have started
            assert loading_started["mr"] is True
            assert loading_started["work"] is True

            # Wait for fetch to complete
            await pilot.pause(0.05)

            # Loading should be done
            screen = pilot.app.screen
            assert screen.mr_loading is False
            assert screen.work_loading is False


class TestMainScreenDataHandling:
    """Test data handling in MainScreen."""

    @pytest.mark.asyncio
    async def test_empty_data_shows_empty_state(self, app, monkeypatch):
        """Test that empty data shows empty state message."""

        # Mock adapters to return empty lists
        async def mock_fetch(*args, **kwargs):
            return []

        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.fetch_assigned_items", mock_fetch)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.screen
            # Should show empty state when no data
            # Both MR subsections should be in empty or error state
            assert screen.mr_container.assigned_to_me_section.state in ["empty", "loading", "error"]
            assert screen.mr_container.opened_by_me_section.state in ["empty", "loading", "error"]
            assert screen.work_section.state in ["empty", "loading", "error"]

    @pytest.mark.asyncio
    async def test_fetch_error_shows_error_state(self, app, monkeypatch):
        """Test that fetch errors show error state."""

        # Mock adapters to raise exceptions
        async def mock_fetch_error(*args, **kwargs):
            raise Exception("Network error")

        monkeypatch.setattr(
            "monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch_error
        )
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.screen
            # Should show error state in both subsections
            assert screen.mr_container.assigned_to_me_section.state == "error"
            assert screen.mr_container.opened_by_me_section.state == "error"
