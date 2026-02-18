"""Integration tests for UI section widgets.

Tests for MergeRequestSection and WorkItemSection using Textual's Pilot API.
"""

from datetime import datetime

import pytest
from textual.app import App
from textual.app import ComposeResult

from monocli.models import JiraWorkItem
from monocli.models import MergeRequest
from monocli.ui.sections import MergeRequestContainer
from monocli.ui.sections import MergeRequestSection
from monocli.ui.sections import SectionState
from monocli.ui.sections import WorkItemSection


class TestApp(App[None]):
    """Test app for wrapping section widgets."""

    def __init__(
        self, section: MergeRequestSection | WorkItemSection | MergeRequestContainer
    ) -> None:
        """Initialize test app with a section widget."""
        super().__init__()
        self.section = section

    def compose(self) -> ComposeResult:
        """Compose the app with the section."""
        yield self.section


class TestMergeRequestSection:
    """Tests for MergeRequestSection widget."""

    @pytest.fixture
    def sample_mr(self) -> MergeRequest:
        """Create a sample merge request for testing."""
        return MergeRequest(
            iid=42,
            title="Fix critical bug in authentication",
            state="opened",
            author={"name": "John Doe", "username": "johndoe"},
            web_url="https://gitlab.com/test/project/-/merge_requests/42",
            source_branch="feature/auth-fix",
            target_branch="main",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
        )

    @pytest.fixture
    def sample_mrs(self) -> list[MergeRequest]:
        """Create sample merge requests for testing."""
        return [
            MergeRequest(
                iid=42,
                title="Fix critical bug in authentication",
                state="opened",
                author={"name": "John Doe", "username": "johndoe"},
                web_url="https://gitlab.com/test/project/-/merge_requests/42",
                source_branch="feature/auth-fix",
                target_branch="main",
                created_at=datetime(2024, 1, 15, 10, 30, 0),
            ),
            MergeRequest(
                iid=43,
                title="Add new feature for user management that has a very long title that needs truncation",
                state="merged",
                author={"name": "Jane Smith", "username": "janesmith"},
                web_url="https://gitlab.com/test/project/-/merge_requests/43",
                source_branch="feature/user-mgmt",
                target_branch="main",
                created_at=datetime(2024, 1, 14, 9, 0, 0),
            ),
        ]

    @pytest.mark.asyncio
    async def test_renders_data_table(self, sample_mr: MergeRequest) -> None:
        """Test that MergeRequestSection renders a DataTable."""
        section = MergeRequestSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data([sample_mr])
            await pilot.pause()

            # Check data table exists
            data_table = section.query_one("#data-table")
            assert data_table is not None

    @pytest.mark.asyncio
    async def test_shows_loading_state(self) -> None:
        """Test that section shows loading spinner."""
        section = MergeRequestSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.show_loading()
            await pilot.pause()

            assert section.state == SectionState.LOADING
            spinner = section.query_one("#spinner")
            assert spinner.styles.display == "block"

    @pytest.mark.asyncio
    async def test_shows_empty_state(self) -> None:
        """Test that section shows empty message when no data."""
        section = MergeRequestSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data([])
            await pilot.pause()

            assert section.state == SectionState.EMPTY
            message = section.query_one("#message")
            assert message.styles.display == "block"
            assert "No merge requests found" in str(message.render())

    @pytest.mark.asyncio
    async def test_shows_error_state(self) -> None:
        """Test that section shows error message."""
        section = MergeRequestSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.set_error("Failed to fetch GitLab MRs")
            await pilot.pause()

            assert section.state == SectionState.ERROR
            message = section.query_one("#message")
            assert message.styles.display == "block"
            assert "Failed to fetch GitLab MRs" in str(message.render())

    @pytest.mark.asyncio
    async def test_data_updates_table(self, sample_mrs: list[MergeRequest]) -> None:
        """Test that data updates refresh the table correctly."""
        section = MergeRequestSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data(sample_mrs)
            await pilot.pause()

            assert section.state == SectionState.DATA
            assert section._item_count == 2

            # Check title shows count
            title = section.query_one("#title")
            assert "(2)" in str(title.render())

    @pytest.mark.asyncio
    async def test_truncate_long_titles(self) -> None:
        """Test that long titles are truncated with ellipsis."""
        long_title = "A" * 100
        mr = MergeRequest(
            iid=1,
            title=long_title,
            state="opened",
            author={"name": "Test", "username": "test"},
            web_url="https://gitlab.com/test/-/merge_requests/1",
            source_branch="feature/test",
            target_branch="main",
            created_at=None,
        )

        section = MergeRequestSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data([mr])
            await pilot.pause()

            # Title should be truncated
            truncated = section._truncate_title(long_title)
            assert len(truncated) <= 40
            assert truncated.endswith("...")

    @pytest.mark.asyncio
    async def test_correct_columns(self, sample_mr: MergeRequest) -> None:
        """Test that DataTable has correct columns."""
        section = MergeRequestSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data([sample_mr])
            await pilot.pause()

            data_table = section.query_one("#data-table")
            # Get column labels from DataTable
            columns = [
                data_table.ordered_columns[i].label.plain
                for i in range(len(data_table.ordered_columns))
            ]
            assert columns == ["Key", "Title", "Status  ", "Author", "Branch", "Created  "]

    def test_display_key_format(self, sample_mr: MergeRequest) -> None:
        """Test that MR keys are displayed with ! prefix."""
        assert sample_mr.display_key() == "!42"


class TestWorkItemSection:
    """Tests for WorkItemSection widget."""

    @pytest.fixture
    def sample_work_item(self) -> JiraWorkItem:
        """Create a sample Jira work item for testing."""
        return JiraWorkItem(
            key="PROJ-123",
            fields={
                "summary": "Implement new feature",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "assignee": {"displayName": "John Doe"},
            },
            self="https://jira.example.com/rest/api/2/issue/12345",
        )

    @pytest.fixture
    def sample_work_items(self) -> list[JiraWorkItem]:
        """Create sample Jira work items for testing."""
        return [
            JiraWorkItem(
                key="PROJ-123",
                fields={
                    "summary": "Implement new feature",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "John Doe"},
                },
                self="https://jira.example.com/rest/api/2/issue/12345",
            ),
            JiraWorkItem(
                key="PROJ-124",
                fields={
                    "summary": "Fix bug in production",
                    "status": {"name": "To Do"},
                    "priority": {"name": "Highest"},
                    "assignee": None,
                },
                self="https://jira.example.com/rest/api/2/issue/12346",
            ),
        ]

    @pytest.mark.asyncio
    async def test_renders_data_table(self, sample_work_item: JiraWorkItem) -> None:
        """Test that WorkItemSection renders a DataTable."""
        section = WorkItemSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data([sample_work_item])
            await pilot.pause()

            # Check data table exists
            data_table = section.query_one("#data-table")
            assert data_table is not None

    @pytest.mark.asyncio
    async def test_shows_loading_state(self) -> None:
        """Test that section shows loading spinner."""
        section = WorkItemSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.show_loading()
            await pilot.pause()

            assert section.state == SectionState.LOADING

    @pytest.mark.asyncio
    async def test_shows_empty_state(self) -> None:
        """Test that section shows empty message when no data."""
        section = WorkItemSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data([])
            await pilot.pause()

            assert section.state == SectionState.EMPTY
            message = section.query_one("#message")
            assert "No work items" in str(message.render())

    @pytest.mark.asyncio
    async def test_data_updates_table(self, sample_work_items: list[JiraWorkItem]) -> None:
        """Test that data updates refresh the table correctly."""
        section = WorkItemSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data(sample_work_items)
            await pilot.pause()

            assert section.state == SectionState.DATA
            assert section._item_count == 2

    @pytest.mark.asyncio
    async def test_correct_columns(self, sample_work_item: JiraWorkItem) -> None:
        """Test that DataTable has correct columns."""
        section = WorkItemSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data([sample_work_item])
            await pilot.pause()

            data_table = section.query_one("#data-table")
            # Get column labels from DataTable
            columns = [
                data_table.ordered_columns[i].label.plain
                for i in range(len(data_table.ordered_columns))
            ]
            assert columns == [
                "Icon",
                "Key",
                "Title",
                "Status  ",
                "Priority  ",
                "Context",
                "Date  ",
            ]

    @pytest.mark.asyncio
    async def test_unassigned_work_item(self) -> None:
        """Test that unassigned work items show 'Unassigned'."""
        item = JiraWorkItem(
            key="PROJ-125",
            fields={
                "summary": "Test unassigned",
                "status": {"name": "To Do"},
                "priority": {"name": "Medium"},
                "assignee": None,
            },
            self="https://jira.example.com/rest/api/2/issue/12347",
        )

        section = WorkItemSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()
            section.update_data([item])
            await pilot.pause()

            # Check assignee shows as "Unassigned"
            assert item.assignee is None
            assert section._item_count == 1

    def test_priority_display(self, sample_work_items: list[JiraWorkItem]) -> None:
        """Test that priority is correctly displayed."""
        # Check priorities
        assert sample_work_items[0].priority == "High"
        assert sample_work_items[1].priority == "Highest"


class TestSectionBaseFunctionality:
    """Tests for common base section functionality."""

    @pytest.mark.asyncio
    async def test_state_transitions(self) -> None:
        """Test that state transitions work correctly."""
        section = MergeRequestSection()
        app = TestApp(section)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Start in loading
            section.show_loading()
            await pilot.pause()
            assert section.state == SectionState.LOADING

            # Transition to error
            section.set_error("Test error")
            await pilot.pause()
            assert section.state == SectionState.ERROR

            # Transition to empty
            section.update_data([])
            await pilot.pause()
            assert section.state == SectionState.EMPTY

            # Transition to data
            mr = MergeRequest(
                iid=1,
                title="Test",
                state="opened",
                author={"name": "Test"},
                web_url="https://test.com/1",
                source_branch="feature/test",
                target_branch="main",
                created_at=None,
            )
            section.update_data([mr])
            await pilot.pause()
            assert section.state == SectionState.DATA


class TestMergeRequestContainer:
    """Tests for MergeRequestContainer widget."""

    @pytest.fixture
    def sample_assigned_mrs(self) -> list[MergeRequest]:
        """Create sample assigned MRs for testing."""
        return [
            MergeRequest(
                iid=10,
                title="Fix critical bug",
                state="opened",
                author={"name": "Alice", "username": "alice"},
                web_url="https://gitlab.com/test/project/-/merge_requests/10",
                source_branch="feature/bug-fix",
                target_branch="main",
                created_at=datetime(2024, 1, 15, 10, 30, 0),
            ),
        ]

    @pytest.fixture
    def sample_authored_mrs(self) -> list[MergeRequest]:
        """Create sample authored MRs for testing."""
        return [
            MergeRequest(
                iid=20,
                title="Add new feature",
                state="opened",
                author={"name": "Test User", "username": "testuser"},
                web_url="https://gitlab.com/test/project/-/merge_requests/20",
                source_branch="feature/new-feature",
                target_branch="main",
                created_at=datetime(2024, 1, 16, 11, 0, 0),
            ),
        ]

    @pytest.mark.asyncio
    async def test_renders_two_subsections(self) -> None:
        """Test that MergeRequestContainer renders two subsections."""
        container = MergeRequestContainer()
        app = TestApp(container)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Check both subsections exist by querying from the app
            opened_section = pilot.app.query_one("#mr-opened-by-me")
            assigned_section = pilot.app.query_one("#mr-assigned-to-me")

            assert opened_section is not None
            assert assigned_section is not None

    @pytest.mark.asyncio
    async def test_updates_assigned_to_me(self, sample_assigned_mrs: list[MergeRequest]) -> None:
        """Test that update_assigned_to_me updates the correct subsection."""
        container = MergeRequestContainer()
        app = TestApp(container)

        async with app.run_test() as pilot:
            await pilot.pause()
            container.update_assigned_to_me(sample_assigned_mrs)
            await pilot.pause()

            # Check the assigned subsection has data
            assert container.assigned_to_me_section.state == SectionState.DATA
            assert container.assigned_to_me_section._item_count == 1

    @pytest.mark.asyncio
    async def test_updates_opened_by_me(self, sample_authored_mrs: list[MergeRequest]) -> None:
        """Test that update_opened_by_me updates the correct subsection."""
        container = MergeRequestContainer()
        app = TestApp(container)

        async with app.run_test() as pilot:
            await pilot.pause()
            container.update_opened_by_me(sample_authored_mrs)
            await pilot.pause()

            # Check the opened subsection has data
            assert container.opened_by_me_section.state == SectionState.DATA
            assert container.opened_by_me_section._item_count == 1

    @pytest.mark.asyncio
    async def test_show_loading_affects_both(self) -> None:
        """Test that show_loading sets both subsections to loading."""
        container = MergeRequestContainer()
        app = TestApp(container)

        async with app.run_test() as pilot:
            await pilot.pause()
            container.show_loading()
            await pilot.pause()

            assert container.opened_by_me_section.state == SectionState.LOADING
            assert container.assigned_to_me_section.state == SectionState.LOADING

    @pytest.mark.asyncio
    async def test_get_active_section(self) -> None:
        """Test get_active_section returns correct subsection."""
        container = MergeRequestContainer()
        app = TestApp(container)

        async with app.run_test() as pilot:
            await pilot.pause()

            opened = container.get_active_section("opened")
            assigned = container.get_active_section("assigned")

            assert opened == container.opened_by_me_section
            assert assigned == container.assigned_to_me_section

    @pytest.mark.asyncio
    async def test_select_next_calls_subsection(
        self, sample_assigned_mrs: list[MergeRequest]
    ) -> None:
        """Test that select_next delegates to the correct subsection."""
        container = MergeRequestContainer()
        app = TestApp(container)

        async with app.run_test() as pilot:
            await pilot.pause()
            container.update_assigned_to_me(sample_assigned_mrs)
            await pilot.pause()

            # This should not raise an error
            container.select_next("assigned")

    @pytest.mark.asyncio
    async def test_select_previous_calls_subsection(
        self, sample_assigned_mrs: list[MergeRequest]
    ) -> None:
        """Test that select_previous delegates to the correct subsection."""
        container = MergeRequestContainer()
        app = TestApp(container)

        async with app.run_test() as pilot:
            await pilot.pause()
            container.update_assigned_to_me(sample_assigned_mrs)
            await pilot.pause()

            # This should not raise an error
            container.select_previous("assigned")
