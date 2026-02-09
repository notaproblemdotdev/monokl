"""Section widgets for displaying merge requests and work items.

This module provides reusable section widgets using Textual's DataTable
to display merge requests and work items with loading, empty, and error states.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Label, LoadingIndicator, Static

if TYPE_CHECKING:
    from monocli.models import JiraWorkItem, MergeRequest


class SectionState:
    """Enum-like class for section states."""

    LOADING = "loading"
    EMPTY = "empty"
    ERROR = "error"
    DATA = "data"


class BaseSection(Static):
    """Base class for data display sections.

    Provides common functionality for loading states, error handling,
    and data display using Textual's DataTable widget.
    """

    # Reactive state
    state: reactive[str] = reactive(SectionState.LOADING)
    error_message: reactive[str] = reactive("")

    DEFAULT_CSS = """
    BaseSection {
        height: 100%;
        width: 100%;
    }

    BaseSection #header {
        height: auto;
        padding: 0;
        margin: 0 0 1 0;
    }

    BaseSection #title {
        padding: 0;
        margin: 0;
    }

    BaseSection #content {
        height: 1fr;
        width: 100%;
    }

    BaseSection #spinner-container {
        display: none;
        height: 100%;
        width: 100%;
        content-align: center middle;
    }

    BaseSection #data-table {
        height: 100%;
        width: 100%;
    }

    BaseSection #message {
        height: 100%;
        width: 100%;
        content-align: center middle;
    }
    """

    def __init__(self, title: str, *args: object, **kwargs: object) -> None:
        """Initialize the base section.

        Args:
            title: The section title to display.
            *args: Additional positional arguments for Static.
            **kwargs: Additional keyword arguments for Static.
        """
        super().__init__(*args, **kwargs)
        self.section_title = title
        self._data_table: DataTable[str] | None = None

    def compose(self) -> ComposeResult:
        """Compose the section layout."""
        with Vertical():
            # Header with title
            with Horizontal(id="header"):
                yield Label(self.section_title, id="title")

            # Content area for data table, loading indicator, or messages
            with Vertical(id="content"):
                with Vertical(id="spinner-container"):
                    yield LoadingIndicator(id="spinner")
                yield DataTable[str](id="data-table")
                yield Label("", id="message")

    def on_mount(self) -> None:
        """Handle mount event."""
        self._data_table = self.query_one("#data-table", DataTable)
        self._update_visibility()

    def watch_state(self) -> None:
        """React to state changes."""
        self._update_visibility()

    def _update_visibility(self) -> None:
        """Update widget visibility based on current state."""
        spinner = self.query_one("#spinner", LoadingIndicator)
        spinner_container = self.query_one("#spinner-container", Vertical)
        table = self.query_one("#data-table", DataTable)
        message = self.query_one("#message", Label)

        if self.state == SectionState.LOADING:
            spinner.styles.display = "block"
            spinner_container.styles.display = "block"
            table.styles.display = "none"
            message.styles.display = "none"
        elif self.state == SectionState.EMPTY:
            spinner.styles.display = "none"
            spinner_container.styles.display = "none"
            table.styles.display = "none"
            message.styles.display = "block"
            message.update(self._get_empty_message())
        elif self.state == SectionState.ERROR:
            spinner.styles.display = "none"
            spinner_container.styles.display = "none"
            table.styles.display = "none"
            message.styles.display = "block"
            message.update(f"Error: {self.error_message}")
            message.add_class("error")
        else:  # DATA state
            spinner.styles.display = "none"
            spinner_container.styles.display = "none"
            table.styles.display = "block"
            message.styles.display = "none"

        # Update title with count if in DATA state
        title_label = self.query_one("#title", Label)
        if self.state == SectionState.DATA and hasattr(self, "_item_count"):
            title_label.update(f"{self.section_title} ({self._item_count})")
        else:
            title_label.update(self.section_title)

    def _get_empty_message(self) -> str:
        """Get the empty state message. Override in subclasses."""
        return "No items found"

    def show_loading(self) -> None:
        """Set section to loading state."""
        self.state = SectionState.LOADING

    def set_error(self, message: str) -> None:
        """Set section to error state with message.

        Args:
            message: The error message to display.
        """
        self.error_message = message
        self.state = SectionState.ERROR

    def _truncate_title(self, title: str, max_length: int = 40) -> str:
        """Truncate title with ellipsis if too long.

        Args:
            title: The title to truncate.
            max_length: Maximum length before truncation.

        Returns:
            Truncated title with ellipsis if needed.
        """
        if len(title) <= max_length:
            return title
        return title[: max_length - 3] + "..."

    def _format_date(self, dt: datetime | None) -> str:
        """Format datetime for display.

        Args:
            dt: The datetime to format.

        Returns:
            Formatted date string or empty string if None.
        """
        if dt is None:
            return ""
        return dt.strftime("%Y-%m-%d")

    def focus_table(self) -> None:
        """Focus the internal DataTable widget.

        Enables keyboard navigation within the table when this
        section becomes the active section.
        """
        if self._data_table is not None:
            self._data_table.focus()

    def select_next(self) -> None:
        """Move selection to the next row in the DataTable.

        Wraps DataTable's cursor movement to navigate down.
        """
        if self._data_table is not None and self.state == SectionState.DATA:
            self._data_table.action_cursor_down()

    def select_previous(self) -> None:
        """Move selection to the previous row in the DataTable.

        Wraps DataTable's cursor movement to navigate up.
        """
        if self._data_table is not None and self.state == SectionState.DATA:
            self._data_table.action_cursor_up()


class MergeRequestSection(BaseSection):
    """Section widget for displaying merge requests.

    Displays merge requests in a DataTable with columns:
    - Key (MR number with ! prefix)
    - Title (truncated if too long)
    - Status (OPENED, CLOSED, etc.)
    - Author (author name or login)
    - Branch (source branch)
    - Created (date)
    """

    merge_requests: reactive[list[MergeRequest]] = reactive([])

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the merge request section."""
        super().__init__("Merge Requests", *args, **kwargs)
        self._item_count = 0

    def _get_empty_message(self) -> str:
        """Return empty state message for MRs."""
        return "No merge requests found"

    def on_mount(self) -> None:
        """Handle mount event and setup table."""
        super().on_mount()
        if self._data_table:
            self._setup_table()

    def _setup_table(self) -> None:
        """Setup DataTable columns."""
        table = self._data_table
        if table is None:
            return

        table.cursor_type = "row"
        table.zebra_stripes = True
        table.show_header = True
        table.add_columns(
            "Key",
            "Title",
            "Status",
            "Author",
            "Branch",
            "Created",
        )

    def watch_merge_requests(self) -> None:
        """React to merge requests data changes."""
        self.update_data(self.merge_requests)

    def update_data(self, merge_requests: list[MergeRequest]) -> None:
        """Update the section with merge request data.

        Args:
            merge_requests: List of MergeRequest models to display.
        """
        self.merge_requests = merge_requests
        self._item_count = len(merge_requests)

        if self._data_table is None:
            return

        # Clear existing rows
        self._data_table.clear()

        if not merge_requests:
            self.state = SectionState.EMPTY
            return

        # Add rows
        for mr in merge_requests:
            author = mr.author.get("name") or mr.author.get("username") or "Unknown"
            created = self._format_date(mr.created_at)

            self._data_table.add_row(
                mr.display_key(),
                self._truncate_title(mr.title),
                mr.display_status(),
                author,
                mr.source_branch,
                created,
                key=str(mr.web_url),  # Store URL for browser opening
            )

        self.state = SectionState.DATA

    def get_selected_url(self) -> str | None:
        """Get the URL of the currently selected row.

        Returns:
            The URL of the selected MR, or None if no selection.
        """
        if self._data_table is None:
            return None

        # cursor_row is the index (0, 1, 2, ...)
        row_index = self._data_table.cursor_row
        if row_index is None:
            return None

        # Get the row key at the cursor index
        try:
            # Get the row coordinate and extract the key
            row_keys = list(self._data_table.rows.keys())
            if row_index < 0 or row_index >= len(row_keys):
                return None

            # The row key is the URL we stored when adding the row
            row_key = row_keys[row_index]
            if hasattr(row_key, "value"):
                return str(row_key.value)
            elif isinstance(row_key, str):
                return row_key

            # Fallback: try to get row data and find MR
            row = self._data_table.get_row_at(row_index)
            if row:
                key = row[0]  # Key column
                for mr in self.merge_requests:
                    if mr.display_key() == key:
                        return str(mr.web_url)
        except (KeyError, IndexError, AttributeError):
            pass

        return None


class MergeRequestContainer(Static):
    """Container for merge request sections with responsive layout.

    Displays two subsections:
    - "Opened by me": MRs authored by the current user
    - "Assigned to me": MRs assigned to the current user

    Uses responsive layout: two columns when terminal is wide (>= 100 cols),
    two rows when terminal is narrow (< 100 cols).
    """

    DEFAULT_CSS = """
    MergeRequestContainer {
        height: 100%;
        width: 100%;
    }

    #mr-subsections {
        height: 100%;
        width: 100%;
    }

    #mr-subsections > MergeRequestSection {
        width: 50%;
        height: 100%;
    }

    #mr-subsections.vertical > MergeRequestSection {
        width: 100%;
        height: 50%;
    }
    """

    # Width threshold for switching between horizontal and vertical layout
    LAYOUT_THRESHOLD = 100

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the MR container with two subsections."""
        super().__init__(*args, **kwargs)
        self.opened_by_me_section = MergeRequestSection(id="mr-opened-by-me")
        self.opened_by_me_section.section_title = "Opened by me"
        self.assigned_to_me_section = MergeRequestSection(id="mr-assigned-to-me")
        self.assigned_to_me_section.section_title = "Assigned to me"

    def compose(self) -> ComposeResult:
        """Compose the container with two MR subsections."""
        with Vertical(id="mr-subsections"):
            yield self.assigned_to_me_section
            yield self.opened_by_me_section

    def on_mount(self) -> None:
        """Handle mount event - set initial layout based on size."""
        self._update_layout()

    def on_resize(self) -> None:
        """Handle resize event - update layout based on new size."""
        self._update_layout()

    def _update_layout(self) -> None:
        """Update layout direction based on container width.

        Uses horizontal layout (columns) when wide, vertical layout (rows) when narrow.
        """
        subsections = self.query_one("#mr-subsections", Vertical)
        width = self.size.width

        if width < self.LAYOUT_THRESHOLD:
            # Narrow terminal: use vertical layout (rows)
            subsections.styles.layout = "vertical"
            subsections.add_class("vertical")
        else:
            # Wide terminal: use horizontal layout (columns)
            subsections.styles.layout = "horizontal"
            subsections.remove_class("vertical")

    def show_loading(self) -> None:
        """Set both subsections to loading state."""
        self.opened_by_me_section.show_loading()
        self.assigned_to_me_section.show_loading()

    def set_error(self, message: str) -> None:
        """Set both subsections to error state.

        Args:
            message: The error message to display.
        """
        self.opened_by_me_section.set_error(message)
        self.assigned_to_me_section.set_error(message)

    def update_opened_by_me(self, merge_requests: list[MergeRequest]) -> None:
        """Update the "Opened by me" subsection.

        Args:
            merge_requests: List of MRs authored by the current user.
        """
        self.opened_by_me_section.update_data(merge_requests)

    def update_assigned_to_me(self, merge_requests: list[MergeRequest]) -> None:
        """Update the "Assigned to me" subsection.

        Args:
            merge_requests: List of MRs assigned to the current user.
        """
        self.assigned_to_me_section.update_data(merge_requests)

    def get_active_section(self, section_type: str) -> MergeRequestSection | None:
        """Get one of the subsections by type.

        Args:
            section_type: Either "opened" or "assigned".

        Returns:
            The requested subsection, or None if invalid type.
        """
        if section_type == "opened":
            return self.opened_by_me_section
        elif section_type == "assigned":
            return self.assigned_to_me_section
        return None

    def get_selected_url(self, section_type: str) -> str | None:
        """Get the URL of the selected item in a subsection.

        Args:
            section_type: Either "opened" or "assigned".

        Returns:
            The URL of the selected MR, or None if no selection.
        """
        section = self.get_active_section(section_type)
        if section:
            return section.get_selected_url()
        return None

    def focus_section(self, section_type: str) -> None:
        """Focus a specific subsection.

        Args:
            section_type: Either "opened" or "assigned".
        """
        section = self.get_active_section(section_type)
        if section:
            section.focus_table()

    def select_next(self, section_type: str) -> None:
        """Move selection down in a subsection.

        Args:
            section_type: Either "opened" or "assigned".
        """
        section = self.get_active_section(section_type)
        if section:
            section.select_next()

    def select_previous(self, section_type: str) -> None:
        """Move selection up in a subsection.

        Args:
            section_type: Either "opened" or "assigned".
        """
        section = self.get_active_section(section_type)
        if section:
            section.select_previous()


class WorkItemSection(BaseSection):
    """Section widget for displaying Jira work items.

    Displays work items in a DataTable with columns:
    - Key (Jira issue key like PROJ-123)
    - Title (truncated if too long)
    - Status (TODO, IN PROGRESS, etc.)
    - Priority (High, Medium, etc.)
    - Assignee (display name or Unassigned)
    - Created (date if available)
    """

    work_items: reactive[list[JiraWorkItem]] = reactive([])

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the work item section."""
        super().__init__("Work Items", *args, **kwargs)
        self._item_count = 0

    def _get_empty_message(self) -> str:
        """Return empty state message for work items."""
        return "No assigned work items"

    def on_mount(self) -> None:
        """Handle mount event and setup table."""
        super().on_mount()
        if self._data_table:
            self._setup_table()

    def _setup_table(self) -> None:
        """Setup DataTable columns."""
        table = self._data_table
        if table is None:
            return

        table.cursor_type = "row"
        table.zebra_stripes = True
        table.show_header = True
        table.add_columns(
            "Key",
            "Title",
            "Status",
            "Priority",
            "Assignee",
            "Created",
        )

    def watch_work_items(self) -> None:
        """React to work items data changes."""
        self.update_data(self.work_items)

    def update_data(self, work_items: list[JiraWorkItem]) -> None:
        """Update the section with work item data.

        Args:
            work_items: List of JiraWorkItem models to display.
        """
        self.work_items = work_items
        self._item_count = len(work_items)

        if self._data_table is None:
            return

        # Clear existing rows
        self._data_table.clear()

        if not work_items:
            self.state = SectionState.EMPTY
            return

        # Add rows
        for item in work_items:
            assignee = item.assignee or "Unassigned"
            # Jira items don't have created_at in our model, so we show empty
            created = ""

            self._data_table.add_row(
                item.display_key(),
                self._truncate_title(item.summary),
                item.display_status(),
                item.priority,
                assignee,
                created,
                key=item.url,  # Store URL for browser opening
            )

        self.state = SectionState.DATA

    def get_selected_url(self) -> str | None:
        """Get the URL of the currently selected row.

        Returns:
            The URL of the selected work item, or None if no selection.
        """
        if self._data_table is None:
            return None

        # cursor_row is the index (0, 1, 2, ...)
        row_index = self._data_table.cursor_row
        if row_index is None:
            return None

        # Get the row key at the cursor index
        try:
            # Get the row coordinate and extract the key
            row_keys = list(self._data_table.rows.keys())
            if row_index < 0 or row_index >= len(row_keys):
                return None

            # The row key is the URL we stored when adding the row
            row_key = row_keys[row_index]
            if isinstance(row_key, str):
                return row_key

            # Fallback: try to get row data and find work item
            row = self._data_table.get_row_at(row_index)
            if row:
                key = row[0]  # Key column
                for item in self.work_items:
                    if item.display_key() == key:
                        return item.url
        except (KeyError, IndexError, AttributeError):
            pass

        return None
