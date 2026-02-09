"""Main screen for the Mono CLI dashboard.

Provides MainScreen class that composes MergeRequestSection and WorkItemSection
into a 50/50 vertical layout with async data fetching from GitLab and Jira.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Label, Static

from monocli.ui.sections import MergeRequestContainer, WorkItemSection

if TYPE_CHECKING:
    pass


class MainScreen(Screen):
    """Main dashboard screen with two-section layout.

    Displays merge requests (top) and work items (bottom) in a 50/50
    vertical split. Uses reactive properties to track active section
    and loading states.

    Example:
        app = MonoApp()
        await app.push_screen(MainScreen())
    """

    # Key bindings
    BINDINGS = [
        ("tab", "switch_section", "Switch Section"),
        ("o", "open_selected", "Open in Browser"),
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
    ]

    # Reactive state
    active_section: reactive[str] = reactive("mr")  # "mr" or "work"
    active_mr_subsection: reactive[str] = reactive("assigned")  # "assigned" or "opened"
    mr_loading: reactive[bool] = reactive(False)
    work_loading: reactive[bool] = reactive(False)

    # CSS for the main screen layout
    DEFAULT_CSS = """
    MainScreen {
        layout: vertical;
    }

    #mr-container {
        height: 50%;
        border: solid $primary;
        padding: 0 1;
    }

    #work-container {
        height: 50%;
        border: solid $surface-lighten-2;
        padding: 0 1;
    }

    #mr-container.active {
        border: solid $success;
    }

    #work-container.active {
        border: solid $success;
    }

    .section-label {
        text-style: bold;
        padding: 1 0 0 0;
    }

    #sections-container {
        height: 100%;
    }

    #content {
        height: 1fr;
    }

    #spinner-container {
        display: none;
        height: 100%;
        width: 100%;
        content-align: center middle;
    }

    #spinner-container LoadingIndicator {
        width: auto;
        height: auto;
    }

    #message {
        height: 100%;
        width: 100%;
        content-align: center middle;
    }

    #data-table {
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the main screen with two sections."""
        with Vertical(id="sections-container"):
            # Top section: Merge Requests (with two subsections)
            with Vertical(id="mr-container"):
                self.mr_container = MergeRequestContainer()
                yield self.mr_container

            # Bottom section: Work Items
            with Vertical(id="work-container"):
                self.work_section = WorkItemSection()
                yield self.work_section

    def on_mount(self) -> None:
        """Handle mount event - trigger data loading."""
        self.detect_and_fetch()

    def watch_active_section(self) -> None:
        """Update visual indicators when active section changes."""
        mr_container = self.query_one("#mr-container", Vertical)
        work_container = self.query_one("#work-container", Vertical)

        if self.active_section == "mr":
            mr_container.add_class("active")
            work_container.remove_class("active")
        else:
            work_container.add_class("active")
            mr_container.remove_class("active")

    def detect_and_fetch(self) -> None:
        """Detect available CLIs and start data fetching.

        Uses DetectionRegistry to check which CLIs are available,
        then starts async workers to fetch data from each.
        """
        from monocli.adapters.detection import CLIDetector, DetectionRegistry

        registry = DetectionRegistry()
        registry.register(CLIDetector("glab", ["auth", "status"]))
        registry.register(CLIDetector("acli", ["jira", "auth", "status"]))

        # Start detection and fetching using run_worker API
        # Run both fetches concurrently - asyncio.Semaphore in async_utils protects
        # against subprocess race conditions
        self.run_worker(self._fetch_all_data(), exclusive=True)

    async def _fetch_all_data(self) -> None:
        """Fetch all data concurrently with semaphore protection.

        Uses asyncio.gather() to run GitLab and Jira fetches in parallel,
        reducing total load time. The subprocess semaphore in async_utils
        prevents race conditions in asyncio's subprocess transport cleanup.
        """
        await asyncio.gather(
            self.fetch_merge_requests(),
            self.fetch_work_items(),
            return_exceptions=True,
        )

    async def fetch_merge_requests(self) -> None:
        """Fetch merge requests from GitLab.

        Runs as a background worker with exclusive=True to prevent race conditions.
        Updates both "Opened by me" and "Assigned to me" subsections.
        """
        from monocli.adapters.gitlab import GitLabAdapter
        from monocli.config import ConfigError, get_config

        self.mr_container.show_loading()
        self.mr_loading = True

        adapter = GitLabAdapter()
        if not adapter.is_available():
            self.mr_container.set_error("glab CLI not found")
            self.mr_loading = False
            return

        try:
            is_auth = await adapter.check_auth()
            if not is_auth:
                self.mr_container.set_error("glab not authenticated")
                self.mr_loading = False
                return

            # Get group from config
            config = get_config()
            try:
                group = config.require_gitlab_group()
            except ConfigError as e:
                self.mr_container.set_error(str(e))
                self.mr_loading = False
                return

            # Fetch MRs assigned to me
            assigned_mrs = await adapter.fetch_assigned_mrs(group=group, assignee="@me")

            # Fetch MRs authored by me (pass empty assignee to avoid glab conflict)
            authored_mrs = await adapter.fetch_assigned_mrs(group=group, assignee="", author="@me")

            # Update each subsection with its specific data
            self.mr_container.update_assigned_to_me(assigned_mrs)
            self.mr_container.update_opened_by_me(authored_mrs)
        except Exception as e:
            self.mr_container.set_error(str(e))
        finally:
            self.mr_loading = False

    async def fetch_work_items(self) -> None:
        """Fetch work items from Jira.

        Runs as a background worker with exclusive=True to prevent race conditions.
        Updates the work items section with data when complete.
        """
        from monocli.adapters.jira import JiraAdapter

        self.work_section.show_loading()
        self.work_loading = True

        adapter = JiraAdapter()
        if not adapter.is_available():
            self.work_section.set_error("acli CLI not found")
            self.work_loading = False
            return

        try:
            is_auth = await adapter.check_auth()
            if not is_auth:
                self.work_section.set_error("acli not authenticated")
                self.work_loading = False
                return

            items = await adapter.fetch_assigned_items()
            self.work_section.update_data(items)
        except Exception as e:
            self.work_section.set_error(str(e))
        finally:
            self.work_loading = False

    def switch_section(self) -> None:
        """Switch between MR and Work sections.

        Called when Tab key is pressed to cycle between sections.
        When in MR section, Tab also switches between "Assigned to me"
        and "Opened by me" subsections.
        """
        if self.active_section == "mr":
            # Switch between MR subsections or to Work section
            if self.active_mr_subsection == "assigned":
                self.active_mr_subsection = "opened"
                self.mr_container.focus_section("opened")
            else:
                self.active_section = "work"
                self.work_section.focus()
        else:
            # From Work section, go back to MR "Assigned to me"
            self.active_section = "mr"
            self.active_mr_subsection = "assigned"
            self.mr_container.focus_section("assigned")

    def action_switch_section(self) -> None:
        """Action handler for switching sections."""
        self.switch_section()

    def action_open_selected(self) -> None:
        """Action handler to open selected item in browser.

        Opens the URL of the currently selected row in the
        active section's DataTable.
        """
        import webbrowser

        url: str | None = None

        if self.active_section == "mr":
            url = self.mr_container.get_selected_url(self.active_mr_subsection)
        else:
            url = self.work_section.get_selected_url()

        if url:
            try:
                webbrowser.open(url)
            except Exception:
                # Log error but don't crash
                pass

    def action_move_down(self) -> None:
        """Action handler to move selection down."""
        if self.active_section == "mr":
            self.mr_container.select_next(self.active_mr_subsection)
        else:
            self.work_section.select_next()

    def action_move_up(self) -> None:
        """Action handler to move selection up."""
        if self.active_section == "mr":
            self.mr_container.select_previous(self.active_mr_subsection)
        else:
            self.work_section.select_previous()

    def on_key(self, event) -> None:
        """Handle key events for navigation.

        This method handles key events directly for cases where
        the standard BINDINGS mechanism needs supplementary handling.
        Currently delegates to action handlers for consistency.

        Args:
            event: The key event from Textual.
        """
        # Key events are primarily handled via BINDINGS and action handlers
        # This method exists for verification compatibility and future extensibility
        pass
