"""Main screen for the Mono CLI dashboard.

Provides MainScreen class that composes MergeRequestSection and WorkItemSection
into a 50/50 vertical layout with async data fetching from GitLab and Jira.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Label, Static
from textual.workers import work

from monocli.ui.sections import MergeRequestSection, WorkItemSection

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

    # Reactive state
    active_section: reactive[str] = reactive("mr")  # "mr" or "work"
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
    """

    def compose(self) -> ComposeResult:
        """Compose the main screen with two sections."""
        with Vertical(id="sections-container"):
            # Top section: Merge Requests
            with Vertical(id="mr-container"):
                self.mr_section = MergeRequestSection()
                yield self.mr_section

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
        registry.register(CLIDetector("acli", ["whoami"]))

        # Start detection and fetching
        self.fetch_merge_requests()
        self.fetch_work_items()

    def fetch_merge_requests(self) -> None:
        """Fetch merge requests from GitLab.

        Uses @work(exclusive=True) to prevent race conditions.
        Updates the MR section with data when complete.
        """
        from monocli.adapters.gitlab import GitLabAdapter

        self.mr_section.show_loading()
        self.mr_loading = True

        @work(exclusive=True)
        async def _fetch_mrs() -> None:
            """Worker to fetch merge requests."""
            adapter = GitLabAdapter()
            if not adapter.is_available():
                self.mr_section.set_error("glab CLI not found")
                self.mr_loading = False
                return

            try:
                is_auth = await adapter.check_auth()
                if not is_auth:
                    self.mr_section.set_error("glab not authenticated")
                    self.mr_loading = False
                    return

                mrs = await adapter.fetch_assigned_mrs()
                self.mr_section.update_data(mrs)
            except Exception as e:
                self.mr_section.set_error(str(e))
            finally:
                self.mr_loading = False

        # Start the worker (fire-and-forget)
        _ = _fetch_mrs()

    def fetch_work_items(self) -> None:
        """Fetch work items from Jira.

        Uses @work(exclusive=True) to prevent race conditions.
        Updates the work items section with data when complete.
        """
        from monocli.adapters.jira import JiraAdapter

        self.work_section.show_loading()
        self.work_loading = True

        @work(exclusive=True)
        async def _fetch_work() -> None:
            """Worker to fetch work items."""
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

        # Start the worker (fire-and-forget)
        _ = _fetch_work()

    def switch_section(self) -> None:
        """Switch between MR and Work sections.

        Called when Tab key is pressed to cycle between sections.
        """
        if self.active_section == "mr":
            self.active_section = "work"
            self.work_section.focus()
        else:
            self.active_section = "mr"
            self.mr_section.focus()

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
            url = self.mr_section.get_selected_url()
        else:
            url = self.work_section.get_selected_url()

        if url:
            try:
                webbrowser.open(url)
            except Exception:
                # Log error but don't crash
                pass
