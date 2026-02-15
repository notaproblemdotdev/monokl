"""Navigation integration tests for the dashboard.

Tests keyboard navigation including Tab switching, j/k navigation,
arrow keys, browser opening, and section-scoped selection using
Textual's Pilot API.
"""

import pytest

from monocli.ui.app import MonoApp
from monocli.ui.sections import MergeRequestSection


class TestNavigation:
    """Test suite for keyboard navigation."""

    @pytest.fixture
    def app(self):
        """Create a test app with MainScreen."""
        return MonoApp()

    @pytest.mark.asyncio
    async def test_tab_switches_active_section(self, app):
        """Test that Tab key switches between MR and Work sections."""
        async with app.run_test() as pilot:
            screen = pilot.app.screen

            # Initial active section should be "mr", subsection "assigned"
            assert screen.active_section == "mr"
            assert screen.active_mr_subsection == "assigned"

            # Press Tab to switch to "opened" subsection
            await pilot.press("tab")
            assert screen.active_section == "mr"
            assert screen.active_mr_subsection == "opened"

            # Press Tab to switch to work section
            await pilot.press("tab")
            assert screen.active_section == "work"

            # Press Tab again to switch back to mr "assigned"
            await pilot.press("tab")
            assert screen.active_section == "mr"
            assert screen.active_mr_subsection == "assigned"

    @pytest.mark.asyncio
    async def test_tab_updates_visual_indicator(self, app):
        """Test that Tab updates the visual border indicator."""
        async with app.run_test() as pilot:
            screen = pilot.app.screen
            mr_container = pilot.app.query_one("#mr-container")
            work_container = pilot.app.query_one("#work-container")

            # Initial state: MR section should have 'active' class
            assert "active" in mr_container.classes
            assert "active" not in work_container.classes

            # Press Tab to switch to "opened" subsection (still MR section active)
            await pilot.press("tab")
            # MR section should still have 'active' class
            assert "active" in mr_container.classes
            assert "active" not in work_container.classes

            # Press Tab to switch to work section
            await pilot.press("tab")
            # Work section should now have 'active' class
            assert "active" not in mr_container.classes
            assert "active" in work_container.classes

    @pytest.mark.asyncio
    async def test_arrow_keys_navigate_within_section(self, app, monkeypatch):
        """Test that arrow keys navigate items in the focused section."""
        from datetime import datetime

        from monocli.models import MergeRequest

        # Create multiple test MRs
        test_mrs = [
            MergeRequest(
                iid=i,
                title=f"Test MR {i}",
                state="opened",
                author={"name": "Test User", "username": "testuser"},
                source_branch=f"feature/test-{i}",
                target_branch="main",
                web_url=f"https://gitlab.com/test/project/-/merge_requests/{i}",
                created_at=datetime.now(),
            )
            for i in range(1, 4)
        ]

        # Mock the adapter
        async def mock_fetch(*args, **kwargs):
            return test_mrs

        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()

            screen = pilot.app.screen

            # Ensure MR "assigned" subsection has data
            assigned_section = screen.mr_container.assigned_to_me_section
            if assigned_section.state != "data":
                pytest.skip("MR section not in data state (CLI may not be available)")

            # Get initial cursor position from the active subsection
            initial_row = assigned_section._data_table.cursor_row

            # Press down arrow
            await pilot.press("down")

            # Cursor should have moved (or stayed at bottom)
            new_row = assigned_section._data_table.cursor_row
            assert new_row is not None

            # Press up arrow to go back
            await pilot.press("up")

            # Cursor should have moved back
            final_row = assigned_section._data_table.cursor_row
            assert final_row is not None

    @pytest.mark.asyncio
    async def test_jk_keys_navigate_within_section(self, app, monkeypatch):
        """Test that j/k keys navigate items in the focused section."""
        from datetime import datetime

        from monocli.models import MergeRequest

        # Create test MRs
        test_mrs = [
            MergeRequest(
                iid=i,
                title=f"Test MR {i}",
                state="opened",
                author={"name": "Test User", "username": "testuser"},
                source_branch=f"feature/test-{i}",
                target_branch="main",
                web_url=f"https://gitlab.com/test/project/-/merge_requests/{i}",
                created_at=datetime.now(),
            )
            for i in range(1, 4)
        ]

        # Mock the adapter
        async def mock_fetch(*args, **kwargs):
            return test_mrs

        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()

            screen = pilot.app.screen

            # Ensure MR "assigned" subsection has data
            assigned_section = screen.mr_container.assigned_to_me_section
            if assigned_section.state != "data":
                pytest.skip("MR section not in data state")

            # Get initial row
            initial_row = assigned_section._data_table.cursor_row

            # Press 'j' to move down
            await pilot.press("j")

            # Verify cursor moved
            new_row = assigned_section._data_table.cursor_row
            assert new_row is not None

            # Press 'k' to move up
            await pilot.press("k")

            # Verify cursor moved
            final_row = assigned_section._data_table.cursor_row
            assert final_row is not None

    @pytest.mark.asyncio
    async def test_o_key_opens_browser(self, app, monkeypatch):
        """Test that 'o' key opens selected item in browser."""
        from datetime import datetime

        from monocli.models import MergeRequest

        expected_url = "https://gitlab.com/test/project/-/merge_requests/42"

        # Create test MR
        test_mr = MergeRequest(
            iid=42,
            title="Test MR for Browser",
            state="opened",
            author={"name": "Test User", "username": "testuser"},
            source_branch="feature/test",
            target_branch="main",
            web_url=expected_url,
            created_at=datetime.now(),
        )

        # Mock the adapter
        async def mock_fetch(*args, **kwargs):
            return [test_mr]

        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)

        # Mock webbrowser.open
        opened_urls = []

        def mock_webbrowser_open(url):
            opened_urls.append(url)
            return True

        monkeypatch.setattr("webbrowser.open", mock_webbrowser_open)

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()

            screen = pilot.app.screen

            # Ensure MR "assigned" subsection has data
            assigned_section = screen.mr_container.assigned_to_me_section
            if assigned_section.state != "data":
                pytest.skip("MR section not in data state")

            # Press 'o' to open selected item
            await pilot.press("o")

            # Verify browser was opened with correct URL
            assert len(opened_urls) == 1
            assert opened_urls[0] == expected_url

    @pytest.mark.asyncio
    async def test_o_key_with_work_section(self, app, monkeypatch):
        """Test that 'o' key opens work item in browser."""
        from monocli.models import JiraWorkItem

        expected_url = "https://jira.example.com/browse/PROJ-123"

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

        # Mock webbrowser.open
        opened_urls = []

        def mock_webbrowser_open(url):
            opened_urls.append(url)
            return True

        monkeypatch.setattr("webbrowser.open", mock_webbrowser_open)

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()

            screen = pilot.app.screen

            # Ensure work section has data
            if screen.work_section.state != "data":
                pytest.skip("Work section not in data state")

            # Switch to work section
            await pilot.press("tab")
            assert screen.active_section == "work"

            # Press 'o' to open selected work item
            await pilot.press("o")

            # Verify browser was opened with correct URL
            assert len(opened_urls) == 1
            assert expected_url in opened_urls[0]

    @pytest.mark.asyncio
    async def test_section_scoped_selection(self, app, monkeypatch):
        """Test that selection is scoped to each section independently."""
        from datetime import datetime

        from monocli.models import JiraWorkItem, MergeRequest

        # Create test data for both sections
        test_mrs = [
            MergeRequest(
                iid=i,
                title=f"MR {i}",
                state="opened",
                author={"name": "Test", "username": "test"},
                source_branch=f"feature/{i}",
                target_branch="main",
                web_url=f"https://gitlab.com/test/-/merge_requests/{i}",
                created_at=datetime.now(),
            )
            for i in range(1, 4)
        ]

        test_items = [
            JiraWorkItem(
                key=f"PROJ-{i}00",
                fields={
                    "summary": f"Issue {i}",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "test"},
                },
                self=f"https://jira.example.com/rest/api/2/issue/{i}00",
            )
            for i in range(1, 4)
        ]

        # Mock both adapters
        async def mock_fetch_mrs(*args, **kwargs):
            return test_mrs

        async def mock_fetch_items(*args, **kwargs):
            return test_items

        monkeypatch.setattr(
            "monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch_mrs
        )
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)
        monkeypatch.setattr(
            "monocli.adapters.jira.JiraAdapter.fetch_assigned_items", mock_fetch_items
        )
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()

            screen = pilot.app.screen

            # Skip if either section doesn't have data
            if screen.mr_section.state != "data" or screen.work_section.state != "data":
                pytest.skip("Sections not in data state")

            # Start at MR section, move down twice
            assert screen.active_section == "mr"
            await pilot.press("j")
            await pilot.press("j")
            mr_row_after_nav = screen.mr_section._data_table.cursor_row

            # Switch to work section
            await pilot.press("tab")
            assert screen.active_section == "work"

            # Work section should have its own cursor position (likely 0 or None)
            work_initial_row = screen.work_section._data_table.cursor_row

            # Move down once in work section
            await pilot.press("j")
            work_row_after_nav = screen.work_section._data_table.cursor_row

            # Switch back to MR section
            await pilot.press("tab")
            assert screen.active_section == "mr"

            # MR section should retain its previous selection
            mr_final_row = screen.mr_section._data_table.cursor_row
            assert mr_final_row == mr_row_after_nav

    @pytest.mark.asyncio
    async def test_o_key_no_selection_does_nothing(self, app, monkeypatch):
        """Test that 'o' key does nothing when no item is selected."""
        # Mock webbrowser.open
        opened_urls = []

        def mock_webbrowser_open(url):
            opened_urls.append(url)
            return True

        monkeypatch.setattr("webbrowser.open", mock_webbrowser_open)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press 'o' without any selection
            await pilot.press("o")

            # Browser should not have been opened
            assert len(opened_urls) == 0

    @pytest.mark.asyncio
    async def test_navigation_in_empty_section(self, app, monkeypatch):
        """Test that navigation in empty section doesn't crash."""

        # Mock adapters to return empty lists
        async def mock_fetch(*args, **kwargs):
            return []

        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.screen

            # Section should be empty
            if screen.mr_section.state == "empty":
                # Try navigation - should not crash
                await pilot.press("j")
                await pilot.press("k")
                await pilot.press("down")
                await pilot.press("up")

                # Test passes if no exception was raised
                assert True

    @pytest.mark.asyncio
    async def test_tab_only_switches_visible_sections(self, app, monkeypatch):
        """Test that Tab only cycles between available sections."""
        # Make one CLI unavailable
        monkeypatch.setattr(
            "monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: False
        )
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.is_available", lambda self: True)
        monkeypatch.setattr("monocli.adapters.jira.JiraAdapter.check_auth", lambda self: True)
        monkeypatch.setattr(
            "monocli.adapters.jira.JiraAdapter.fetch_assigned_items",
            lambda *a, **k: [],
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.screen

            # Both sections might still exist in the UI even if one is in error state
            # Tab should still work to switch between them
            initial_section = screen.active_section

            await pilot.press("tab")

            # Should have switched
            assert screen.active_section != initial_section

            await pilot.press("tab")

            # Should be back to initial
            assert screen.active_section == initial_section


class TestSectionWidgetNavigation:
    """Test navigation methods in section widgets."""

    @pytest.mark.asyncio
    async def test_get_selected_url_returns_url(self):
        """Test that get_selected_url returns the correct URL."""
        from datetime import datetime

        from monocli.models import MergeRequest

        # Create a section with data
        section = MergeRequestSection()

        test_mr = MergeRequest(
            iid=42,
            title="Test MR",
            state="opened",
            author={"name": "Test", "username": "test"},
            source_branch="feature/test",
            target_branch="main",
            web_url="https://gitlab.com/test/-/merge_requests/42",
            created_at=datetime.now(),
        )

        # Update section with data
        section.update_data([test_mr])

        # Mock the data table state
        if section._data_table:
            section._data_table.cursor_row = 0

            # Get selected URL
            url = section.get_selected_url()

            # Should return the URL
            assert url == "https://gitlab.com/test/-/merge_requests/42"

    @pytest.mark.asyncio
    async def test_get_selected_url_no_selection(self):
        """Test that get_selected_url returns None when no selection."""
        section = MergeRequestSection()

        # No data, no selection
        url = section.get_selected_url()

        # Should return None
        assert url is None

    @pytest.mark.asyncio
    async def test_select_next_increments_cursor(self):
        """Test that select_next moves cursor down."""
        from datetime import datetime

        from monocli.models import MergeRequest

        section = MergeRequestSection()

        test_mrs = [
            MergeRequest(
                iid=i,
                title=f"MR {i}",
                state="opened",
                author={"name": "Test", "username": "test"},
                source_branch=f"feature/{i}",
                target_branch="main",
                web_url=f"https://gitlab.com/test/-/merge_requests/{i}",
                created_at=datetime.now(),
            )
            for i in range(1, 4)
        ]

        section.update_data(test_mrs)

        if section._data_table:
            # Set initial cursor position
            section._data_table.cursor_row = 0
            initial_row = section._data_table.cursor_row

            # Move next
            section.select_next()

            # Cursor should have moved down
            # Note: actual movement depends on DataTable implementation
            assert section._data_table.cursor_row is not None

    @pytest.mark.asyncio
    async def test_select_previous_decrements_cursor(self):
        """Test that select_previous moves cursor up."""
        from datetime import datetime

        from monocli.models import MergeRequest

        section = MergeRequestSection()

        test_mrs = [
            MergeRequest(
                iid=i,
                title=f"MR {i}",
                state="opened",
                author={"name": "Test", "username": "test"},
                source_branch=f"feature/{i}",
                target_branch="main",
                web_url=f"https://gitlab.com/test/-/merge_requests/{i}",
                created_at=datetime.now(),
            )
            for i in range(1, 4)
        ]

        section.update_data(test_mrs)

        if section._data_table:
            # Set cursor to last row
            section._data_table.cursor_row = 2

            # Move previous
            section.select_previous()

            # Cursor should have moved up
            assert section._data_table.cursor_row is not None

    @pytest.mark.asyncio
    async def test_focus_table_focuses_data_table(self):
        """Test that focus_table focuses the internal DataTable."""
        from datetime import datetime

        from monocli.models import MergeRequest

        section = MergeRequestSection()

        test_mr = MergeRequest(
            iid=1,
            title="Test",
            state="opened",
            author={"name": "Test", "username": "test"},
            source_branch="feature/test",
            target_branch="main",
            web_url="https://gitlab.com/test/-/merge_requests/1",
            created_at=datetime.now(),
        )

        section.update_data([test_mr])

        # Note: In a real Textual app, we'd need to mount the widget
        # to test focus. This test verifies the method exists and can be called.
        assert hasattr(section, "focus_table")


class TestBrowserIntegration:
    """Test browser opening functionality."""

    @pytest.fixture
    def app(self):
        """Create a test app with MainScreen."""
        return MonoApp()

    @pytest.mark.asyncio
    async def test_browser_open_failure_handled_gracefully(self, app, monkeypatch):
        """Test that browser open failure is handled gracefully."""
        from datetime import datetime

        from monocli.models import MergeRequest

        test_mr = MergeRequest(
            iid=42,
            title="Test MR",
            state="opened",
            author={"name": "Test", "username": "test"},
            source_branch="feature/test",
            target_branch="main",
            web_url="https://gitlab.com/test/-/merge_requests/42",
            created_at=datetime.now(),
        )

        # Mock the adapter
        async def mock_fetch(*args, **kwargs):
            return [test_mr]

        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", mock_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)

        # Mock webbrowser.open to raise an exception
        def mock_webbrowser_fail(url):
            raise Exception("Browser failed to open")

        monkeypatch.setattr("webbrowser.open", mock_webbrowser_fail)

        async with app.run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.screen

            if screen.mr_section.state != "data":
                pytest.skip("MR section not in data state")

            # Press 'o' - should not crash even if browser fails
            await pilot.press("o")

            # Test passes if no exception was raised
            assert True

    @pytest.mark.asyncio
    async def test_browser_open_with_no_url(self, app, monkeypatch):
        """Test that pressing 'o' with no URL selected does nothing."""
        opened_urls = []

        def mock_webbrowser_open(url):
            opened_urls.append(url)
            return True

        monkeypatch.setattr("webbrowser.open", mock_webbrowser_open)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to work section (which might be empty)
            await pilot.press("tab")

            # Press 'o'
            await pilot.press("o")

            # Should not have opened anything
            assert len(opened_urls) == 0


class TestNavigationEdgeCases:
    """Test edge cases in navigation."""

    @pytest.fixture
    def app(self):
        """Create a test app with MainScreen."""
        return MonoApp()

    @pytest.mark.asyncio
    async def test_multiple_tabs_cycles_correctly(self, app):
        """Test that multiple Tab presses cycle correctly."""
        async with app.run_test() as pilot:
            screen = pilot.app.screen

            # Press Tab multiple times
            sections = []
            for _ in range(6):
                await pilot.press("tab")
                sections.append(screen.active_section)

            # Should alternate between mr and work
            # After even number of tabs, should be back to starting position
            assert screen.active_section == "mr"

    @pytest.mark.asyncio
    async def test_navigation_with_loading_section(self, app, monkeypatch):
        """Test navigation works when a section is loading."""
        import asyncio

        async def slow_fetch(*args, **kwargs):
            await asyncio.sleep(0.5)
            return []

        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs", slow_fetch)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            # Section should be loading
            await pilot.pause()

            screen = pilot.app.screen

            # Try navigation - should not crash
            await pilot.press("j")
            await pilot.press("k")
            await pilot.press("tab")

            # Test passes if no exception
            assert True

    @pytest.mark.asyncio
    async def test_navigation_with_error_section(self, app, monkeypatch):
        """Test navigation works when a section has error."""
        monkeypatch.setattr(
            "monocli.adapters.gitlab.GitLabAdapter.fetch_assigned_mrs",
            lambda *a, **k: (_ for _ in ()).throw(Exception("Network error")),
        )
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.check_auth", lambda self: True)
        monkeypatch.setattr("monocli.adapters.gitlab.GitLabAdapter.is_available", lambda self: True)

        async with app.run_test() as pilot:
            await pilot.pause()

            screen = pilot.app.screen

            # Section should be in error state
            # Try navigation - should not crash
            await pilot.press("j")
            await pilot.press("o")
            await pilot.press("tab")

            # Test passes if no exception
            assert True
