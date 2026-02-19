"""Section widgets for displaying merge requests and work items.

This module provides reusable section widgets using Textual's DataTable
to display merge requests and work items with loading, empty, and error states.
"""

from __future__ import annotations

import webbrowser
from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import DataTable
from textual.widgets import Label
from textual.widgets import Static

from monocli.ui.sorting import SORT_INDICATOR_NONE
from monocli.ui.sorting import SortMethod
from monocli.ui.sorting import SortState
from monocli.ui.sorting import get_sort_indicator
from monocli.ui.spinner import StatusSpinner

if TYPE_CHECKING:
    from monocli.models import CodeReview
    from monocli.models import PieceOfWork


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

    BINDINGS = [
        Binding("o", "open_selected", "Open in Browser", show=False),
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("f", "enter_sort_mode", "Format"),
        Binding("s", "sort_action", "Sort", show=False),
        Binding("p", "sort_priority", "Priority", show=False),
        Binding("d", "sort_date", "Date", show=False),
        Binding("0", "sort_reset", "Reset", show=False),
        Binding("escape", "exit_sort_mode", "Cancel", show=False),
    ]

    SORT_MODE_NONE = ""
    SORT_MODE_AWAITING_SORT = "awaiting_sort"
    SORT_MODE_AWAITING_METHOD = "awaiting_method"

    _sort_mode: reactive[str] = reactive(SORT_MODE_NONE)

    state: reactive[str] = reactive(SectionState.LOADING)
    error_message: reactive[str] = reactive("")
    loading_status: reactive[str] = reactive("")
    sort_state: reactive[SortState | None] = reactive(None)

    def watch__sort_mode(self) -> None:
        """React to sort mode changes with notification hints."""
        if self._sort_mode == self.SORT_MODE_AWAITING_SORT:
            self.notify("(s)ort", title="Format", timeout=3)
        elif self._sort_mode == self.SORT_MODE_AWAITING_METHOD:
            self.notify(
                "(p)riority  (s)tatus  (d)ate  (0)reset",
                title="Sort",
                timeout=5,
            )

    DEFAULT_CSS = """
    BaseSection {
        height: 100%;
        width: 100%;
    }

    BaseSection #content {
        height: 1fr;
        width: 100%;
        layout: vertical;
    }

    BaseSection #content-wrapper {
        width: 100%;
        height: 1fr;
    }

    BaseSection #spinner-row {
        width: 100%;
        height: auto;
        display: none;
        content-align: right middle;
        padding: 0 1 0 0;
    }

    BaseSection #spinner-row StatusSpinner {
        color: $accent;
    }

    BaseSection #data-table {
        height: 100%;
        width: 100%;
    }

    BaseSection #data-table .datatable--header-cell:first-child,
    BaseSection #data-table .datatable--cell:first-child {
        width: auto;
        min-width: 2;
        padding: 0;
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
        with Vertical(), Vertical(id="content"):
            with Vertical(id="content-wrapper"):
                yield DataTable[str](id="data-table")
                yield Label("", id="message")
            with Horizontal(id="spinner-row"):
                yield StatusSpinner("", id="spinner")

    def on_mount(self) -> None:
        """Handle mount event."""
        self._data_table = self.query_one("#data-table", DataTable)
        self._update_visibility()

    def watch_state(self) -> None:
        """React to state changes."""
        self._update_visibility()

    def _update_visibility(self) -> None:
        """Update widget visibility based on current state."""
        spinner = self.query_one("#spinner", StatusSpinner)
        spinner_row = self.query_one("#spinner-row", Horizontal)
        table = self.query_one("#data-table", DataTable)
        message = self.query_one("#message", Label)

        if self.state == SectionState.LOADING:
            spinner_row.styles.display = "block"
            spinner.start(self.loading_status)
            table.styles.display = "none"
            message.styles.display = "none"
        elif self.state == SectionState.EMPTY:
            spinner_row.styles.display = "none"
            spinner.stop()
            table.styles.display = "none"
            message.styles.display = "block"
            message.update(self._get_empty_message())
        elif self.state == SectionState.ERROR:
            spinner_row.styles.display = "none"
            spinner.stop()
            table.styles.display = "none"
            message.styles.display = "block"
            message.update(f"Error: {self.error_message}")
            message.add_class("error")
        else:  # DATA state
            spinner_row.styles.display = "none"
            spinner.stop()
            table.styles.display = "block"
            message.styles.display = "none"

    def _get_empty_message(self) -> str:
        """Get the empty state message. Override in subclasses."""
        return "No items found"

    def show_loading(self, status: str = "") -> None:
        """Set section to loading state.

        Args:
            status: Optional status message to display with the spinner.
        """
        self.loading_status = status
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

    def action_open_selected(self) -> None:
        """Open the selected item in browser."""
        url = self.get_selected_url()
        if url:
            with suppress(Exception):
                webbrowser.open(url)

    def action_move_down(self) -> None:
        """Action handler to move selection down."""
        self.select_next()

    def action_move_up(self) -> None:
        """Action handler to move selection up."""
        self.select_previous()

    def action_enter_sort_mode(self) -> None:
        """Enter sort mode - first step of f -> s -> p/s/d/0 sequence."""
        self._sort_mode = self.SORT_MODE_AWAITING_SORT

    def action_sort_action(self) -> None:
        """Handle 's' key - either enter method mode or sort by status."""
        if self._sort_mode == self.SORT_MODE_AWAITING_SORT:
            self._sort_mode = self.SORT_MODE_AWAITING_METHOD
        elif self._sort_mode == self.SORT_MODE_AWAITING_METHOD:
            self._apply_sort(SortMethod.STATUS)
            self._sort_mode = self.SORT_MODE_NONE

    def action_exit_sort_mode(self) -> None:
        """Exit sort mode."""
        self._sort_mode = self.SORT_MODE_NONE

    def action_sort_priority(self) -> None:
        """Sort by priority column."""
        if self._sort_mode == self.SORT_MODE_AWAITING_METHOD:
            self._apply_sort(SortMethod.PRIORITY)
            self._sort_mode = self.SORT_MODE_NONE

    def action_sort_status(self) -> None:
        """Sort by status column."""
        if self._sort_mode == self.SORT_MODE_AWAITING_METHOD:
            self._apply_sort(SortMethod.STATUS)
            self._sort_mode = self.SORT_MODE_NONE

    def action_sort_date(self) -> None:
        """Sort by date column."""
        if self._sort_mode == self.SORT_MODE_AWAITING_METHOD:
            self._apply_sort(SortMethod.DATE)
            self._sort_mode = self.SORT_MODE_NONE

    def action_sort_reset(self) -> None:
        """Reset sort to default order."""
        if self._sort_mode == self.SORT_MODE_AWAITING_METHOD:
            self._reset_sort()
            self._sort_mode = self.SORT_MODE_NONE

    def _apply_sort(self, method: SortMethod) -> None:
        """Apply or toggle sort by given method.

        Args:
            method: The sort method to apply.
        """
        if self.sort_state and self.sort_state.method == method:
            self.sort_state = self.sort_state.toggle_direction()
        else:
            self.sort_state = SortState(method=method, descending=True)
        self._perform_sort()
        self._update_header_indicators()

    def _reset_sort(self) -> None:
        """Reset sort to default (no sorting)."""
        self.sort_state = None
        self._perform_sort()
        self._update_header_indicators()

    def _perform_sort(self) -> None:
        """Perform the actual sort on the data table.

        Subclasses should override this to implement section-specific sorting.
        """

    def _update_header_indicators(self) -> None:
        """Update column headers with sort indicators.

        Subclasses should override this to update their specific columns.
        """

    def get_sort_state_dict(self) -> dict[str, Any] | None:
        """Get current sort state as dict for persistence.

        Returns:
            SortState as dict or None if no sort applied.
        """
        if self.sort_state is None:
            return None
        return self.sort_state.to_dict()

    def restore_sort_state(self, state_dict: dict[str, Any]) -> None:
        """Restore sort state from persisted dict.

        Args:
            state_dict: Previously saved sort state.
        """
        try:
            self.sort_state = SortState.from_dict(state_dict)
            self._perform_sort()
            self._update_header_indicators()
        except Exception:
            self.sort_state = None


class CodeReviewSubSection(BaseSection):
    """Subsection widget for displaying code reviews (MRs/PRs).

    Displays code reviews in a DataTable with columns:
    - Key (MR/PR number with ! or # prefix)
    - Title (truncated if too long)
    - Status (OPEN, CLOSED, MERGED, etc.)
    - Author (author name or login)
    - Branch (source branch)
    - Created (date)
    """

    code_reviews: reactive[list[CodeReview]] = reactive([])

    DEFAULT_CSS = """
    CodeReviewSubSection {
        border: round $text-muted;
        border-title-align: left;
        border-subtitle-align: right;
        padding: 0 1;
    }

    CodeReviewSubSection.active {
        border: double $success;
    }

    CodeReviewSubSection.offline {
        border: round $warning;
    }
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the code review subsection."""
        super().__init__("Code Reviews", *args, **kwargs)
        self._item_count = 0
        self._col_keys: dict[str, Any] = {}

    def _get_empty_message(self) -> str:
        """Return empty state message for code reviews."""
        return "No code reviews found"

    def on_mount(self) -> None:
        """Handle mount event and setup table."""
        super().on_mount()
        if self._data_table:
            self._setup_table()
        self._update_border_title()

    def _update_border_title(self) -> None:
        """Update the border title with count."""
        if self.state == SectionState.DATA:
            self.border_title = f"{self.section_title} ({self._item_count})"
        else:
            self.border_title = self.section_title
        self._update_adapter_subtitle()

    def _update_adapter_subtitle(self) -> None:
        """Update border subtitle with adapter icons."""
        adapters = self._get_adapter_info()
        if adapters:
            self.border_subtitle = " · ".join(f"{icon} {name}" for icon, name in adapters)
        else:
            self.border_subtitle = ""

    def _get_adapter_info(self) -> list[tuple[str, str]]:
        """Get unique adapter (icon, name) pairs from current data."""
        if not self.code_reviews:
            return []
        seen: set[str] = set()
        adapters: list[tuple[str, str]] = []
        for cr in self.code_reviews:
            if cr.adapter_type not in seen:
                seen.add(cr.adapter_type)
                adapters.append((cr.adapter_icon, cr.adapter_type.title()))
        return adapters

    def _setup_table(self) -> None:
        """Setup DataTable columns with reserved space for sort indicators."""
        table = self._data_table
        if table is None:
            return

        table.cursor_type = "row"
        table.zebra_stripes = True
        table.show_header = True
        cols = table.add_columns(
            "",
            "Key",
            "Title",
            f"Status{SORT_INDICATOR_NONE}",
            "Author",
            "Branch",
            f"Created{SORT_INDICATOR_NONE}",
        )
        self._col_keys = {
            "status": cols[3],
            "date": cols[6],
        }

    def watch_code_reviews(self) -> None:
        """React to code review data changes."""
        self.update_data(self.code_reviews)

    def update_data(self, code_reviews: list[CodeReview]) -> None:
        """Update the section with code review data.

        Args:
            code_reviews: List of CodeReview models to display.
        """
        self.code_reviews = code_reviews
        self._item_count = len(code_reviews)

        if self._data_table is None:
            return

        # Clear existing rows
        self._data_table.clear()

        if not code_reviews:
            self.state = SectionState.EMPTY
            return

        # Add rows
        for cr in code_reviews:
            created = self._format_date(cr.created_at)

            self._data_table.add_row(
                cr.adapter_icon,
                cr.display_key(),
                self._truncate_title(cr.title),
                cr.display_status(),
                cr.author,
                cr.source_branch,
                created,
                key=cr.url,  # Store URL for browser opening
            )

        self.state = SectionState.DATA

        self._update_border_title()

    def _perform_sort(self) -> None:
        """Sort code reviews by current sort state."""
        if self._data_table is None or not self.code_reviews:
            return

        if self.sort_state is None or self.sort_state.method == SortMethod.NONE:
            return

        from monocli.ui.sorting import get_code_review_sort_key

        sort_method = self.sort_state.method
        sort_descending = self.sort_state.descending

        sorted_reviews = sorted(
            self.code_reviews,
            key=lambda cr: get_code_review_sort_key(cr, sort_method),
            reverse=sort_descending,
        )

        self._data_table.clear()
        for cr in sorted_reviews:
            created = self._format_date(cr.created_at)
            self._data_table.add_row(
                cr.adapter_icon,
                cr.display_key(),
                self._truncate_title(cr.title),
                cr.display_status(),
                cr.author,
                cr.source_branch,
                created,
                key=cr.url,
            )

    def _update_header_indicators(self) -> None:
        """Update column headers with sort indicators."""
        if self._data_table is None:
            return

        status_indicator = SORT_INDICATOR_NONE
        date_indicator = SORT_INDICATOR_NONE

        if self.sort_state:
            indicator = get_sort_indicator(self.sort_state)
            if self.sort_state.method == SortMethod.STATUS:
                status_indicator = indicator
            elif self.sort_state.method == SortMethod.DATE:
                date_indicator = indicator

        if "status" in self._col_keys:
            self._data_table.columns[self._col_keys["status"]].label = Text(
                f"Status{status_indicator}"
            )
        if "date" in self._col_keys:
            self._data_table.columns[self._col_keys["date"]].label = Text(
                f"Created{date_indicator}"
            )

    def get_selected_url(self) -> str | None:
        """Get the URL of the currently selected row.

        Returns:
            The URL of the selected code review, or None if no selection.
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
            if isinstance(row_key, str):
                return row_key

            # Fallback: try to get row data and find code review
            row = self._data_table.get_row_at(row_index)
            if row:
                key = row[0]  # Key column
                for cr in self.code_reviews:
                    if cr.display_key() == key:
                        return cr.url
        except (KeyError, IndexError, AttributeError):
            pass

        return None


# Backwards compatibility alias
MergeRequestSection = CodeReviewSubSection


class CodeReviewSection(Static):
    """Container for code review sections with responsive layout.

    Displays two subsections:
    - "Opened by me": Code reviews authored by the current user
    - "Assigned to me": Code reviews assigned to the current user

    Uses responsive layout: two columns when terminal is wide (>= 100 cols),
    two rows when terminal is narrow (< 100 cols).
    """

    DEFAULT_CSS = """
    CodeReviewSection {
        height: 100%;
        width: 100%;
    }

    #cr-subsections {
        height: 100%;
        width: 100%;
    }

    #cr-subsections > CodeReviewSubSection {
        width: 50%;
        height: 100%;
    }

    #cr-subsections.vertical > CodeReviewSubSection {
        width: 100%;
        height: 50%;
    }
    """

    # Width threshold for switching between horizontal and vertical layout
    LAYOUT_THRESHOLD = 100

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the code review container with two subsections."""
        super().__init__(*args, **kwargs)
        self.opened_by_me_section = CodeReviewSubSection(id="cr-opened-by-me")
        self.opened_by_me_section.section_title = "[2] Code reviews from me"
        self.assigned_to_me_section = CodeReviewSubSection(id="cr-assigned-to-me")
        self.assigned_to_me_section.section_title = "[1] Code reviews for me"

    def compose(self) -> ComposeResult:
        """Compose the container with two code review subsections."""
        with Vertical(id="cr-subsections"):
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
        subsections = self.query_one("#cr-subsections", Vertical)
        width = self.size.width

        if width < self.LAYOUT_THRESHOLD:
            # Narrow terminal: use vertical layout (rows)
            subsections.styles.layout = "vertical"
            subsections.add_class("vertical")
        else:
            # Wide terminal: use horizontal layout (columns)
            subsections.styles.layout = "horizontal"
            subsections.remove_class("vertical")

    def show_loading(self, status: str = "") -> None:
        """Set both subsections to loading state.

        Args:
            status: Optional status message to display with the spinner.
        """
        self.opened_by_me_section.show_loading(status)
        self.assigned_to_me_section.show_loading(status)

    def set_error(self, message: str) -> None:
        """Set both subsections to error state.

        Args:
            message: The error message to display.
        """
        self.opened_by_me_section.set_error(message)
        self.assigned_to_me_section.set_error(message)

    def update_opened_by_me(self, code_reviews: list[CodeReview]) -> None:
        """Update the "Opened by me" subsection.

        Args:
            code_reviews: List of code reviews authored by the current user.
        """
        self.opened_by_me_section.update_data(code_reviews)

    def update_assigned_to_me(self, code_reviews: list[CodeReview]) -> None:
        """Update the "Assigned to me" subsection.

        Args:
            code_reviews: List of code reviews assigned to the current user.
        """
        self.assigned_to_me_section.update_data(code_reviews)

    def get_active_section(self, section_type: str) -> CodeReviewSubSection | None:
        """Get one of the subsections by type.

        Args:
            section_type: Either "opened" or "assigned".

        Returns:
            The requested subsection, or None if invalid type.
        """
        if section_type == "opened":
            return self.opened_by_me_section
        if section_type == "assigned":
            return self.assigned_to_me_section
        return None

    def get_selected_url(self, section_type: str) -> str | None:
        """Get the URL of the selected item in a subsection.

        Args:
            section_type: Either "opened" or "assigned".

        Returns:
            The URL of the selected code review, or None if no selection.
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


# Backwards compatibility alias
MergeRequestContainer = CodeReviewSection


class PieceOfWorkSection(BaseSection):
    """Section widget for displaying pieces of work (Jira, GitHub Issues, Todoist, etc.).

    Displays work items in a DataTable with columns:
    - Icon (adapter icon emoji)
    - Key (Jira issue key, GitHub issue #, Todoist task ID)
    - Title (truncated if too long)
    - Status (TODO, IN PROGRESS, OPEN, DONE, etc.)
    - Priority (numeric priority for sorting)
    - Context (Assignee or project name)
    - Date (due date if available)
    """

    work_items: reactive[list[PieceOfWork]] = reactive([])

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the piece of work section."""
        super().__init__("Work Items", *args, **kwargs)
        self._item_count = 0
        self._col_keys: dict[str, Any] = {}

    def _get_empty_message(self) -> str:
        """Return empty state message for work items."""
        return "No work items"

    def on_mount(self) -> None:
        """Handle mount event and setup table."""
        super().on_mount()
        if self._data_table:
            self._setup_table()
        self._update_border_title()

    def get_adapter_info(self) -> list[tuple[str, str]]:
        """Get unique adapter (icon, name) pairs from current data."""
        if not self.work_items:
            return []
        seen: set[str] = set()
        adapters: list[tuple[str, str]] = []
        for item in self.work_items:
            adapter_type = getattr(item, "adapter_type", None)
            icon = getattr(item, "adapter_icon", None)
            if adapter_type and icon and adapter_type not in seen:
                seen.add(adapter_type)
                adapters.append((icon, adapter_type.title()))
        return adapters

    def _update_border_title(self) -> None:
        """Update the border title with count."""
        if self.state == SectionState.DATA:
            self.border_title = f"{self.section_title} ({self._item_count})"
        else:
            self.border_title = self.section_title
        self._update_adapter_subtitle()

    def _update_adapter_subtitle(self) -> None:
        """Update border subtitle with adapter icons."""
        adapters = self.get_adapter_info()
        if adapters:
            self.border_subtitle = " · ".join(f"{icon} {name}" for icon, name in adapters)
        else:
            self.border_subtitle = ""

    def _setup_table(self) -> None:
        """Setup DataTable columns with reserved space for sort indicators."""
        table = self._data_table
        if table is None:
            return

        table.cursor_type = "row"
        table.zebra_stripes = True
        table.show_header = True
        cols = table.add_columns(
            "",
            "Key",
            "Title",
            f"Status{SORT_INDICATOR_NONE}",
            f"Priority{SORT_INDICATOR_NONE}",
            "Context",
            f"Date{SORT_INDICATOR_NONE}",
        )
        self._col_keys = {
            "status": cols[3],
            "priority": cols[4],
            "date": cols[6],
        }

    def watch_work_items(self) -> None:
        """React to work items data changes."""
        self.update_data(self.work_items)

    def update_data(self, work_items: list[PieceOfWork]) -> None:
        """Update the section with piece of work data.

        Args:
            work_items: List of PieceOfWork models.
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
        added_count = 0
        for item in work_items:
            try:
                icon = item.adapter_icon
                key = item.display_key()
                title = self._truncate_title(item.title)
                status = item.display_status()
                priority = str(item.priority) if item.priority else ""
                context = item.assignee or ""
                date_str = item.due_date or ""
                url = item.url

                self._data_table.add_row(
                    icon,
                    key,
                    title,
                    status,
                    priority,
                    context,
                    date_str,
                    key=url,  # Store URL for browser opening
                )
                added_count += 1
            except Exception:
                # Skip items that fail to process
                continue

        # Show data if we added any rows, otherwise show empty state
        if added_count > 0:
            self.state = SectionState.DATA
        else:
            self.state = SectionState.EMPTY

        self._update_border_title()

    def _perform_sort(self) -> None:
        """Sort work items by current sort state."""
        if self._data_table is None or not self.work_items:
            return

        if self.sort_state is None or self.sort_state.method == SortMethod.NONE:
            return

        from monocli.ui.sorting import get_work_item_sort_key

        sort_method = self.sort_state.method
        sort_descending = self.sort_state.descending

        sorted_items = sorted(
            self.work_items,
            key=lambda item: get_work_item_sort_key(item, sort_method),
            reverse=sort_descending,
        )

        self._data_table.clear()
        for item in sorted_items:
            try:
                icon = item.adapter_icon
                key = item.display_key()
                title = self._truncate_title(item.title)
                status = item.display_status()
                priority = str(item.priority) if item.priority else ""
                context = item.assignee or ""
                date_str = item.due_date or ""
                url = item.url

                self._data_table.add_row(
                    icon,
                    key,
                    title,
                    status,
                    priority,
                    context,
                    date_str,
                    key=url,
                )
            except Exception:
                continue

    def _update_header_indicators(self) -> None:
        """Update column headers with sort indicators."""
        if self._data_table is None:
            return

        status_indicator = SORT_INDICATOR_NONE
        priority_indicator = SORT_INDICATOR_NONE
        date_indicator = SORT_INDICATOR_NONE

        if self.sort_state:
            indicator = get_sort_indicator(self.sort_state)
            if self.sort_state.method == SortMethod.STATUS:
                status_indicator = indicator
            elif self.sort_state.method == SortMethod.PRIORITY:
                priority_indicator = indicator
            elif self.sort_state.method == SortMethod.DATE:
                date_indicator = indicator

        if "status" in self._col_keys:
            self._data_table.columns[self._col_keys["status"]].label = Text(
                f"Status{status_indicator}"
            )
        if "priority" in self._col_keys:
            self._data_table.columns[self._col_keys["priority"]].label = Text(
                f"Priority{priority_indicator}"
            )
        if "date" in self._col_keys:
            self._data_table.columns[self._col_keys["date"]].label = Text(f"Date{date_indicator}")

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
            if hasattr(row_key, "value"):
                return str(row_key.value)
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


# Backwards compatibility alias
WorkItemSection = PieceOfWorkSection
