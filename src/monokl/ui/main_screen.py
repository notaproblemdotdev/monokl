"""Main screen for the Monokl dashboard.

Provides MainScreen class that composes CodeReviewSection and PieceOfWorkSection
into a 50/50 vertical layout with async data fetching from various sources.

Features:
- SQLite caching for offline mode and fast startup
- Non-blocking UI (shows cached data first, then refreshes)
- Automatic offline fallback
- Manual refresh with 'r' key
- Visual indicators for cached vs live data
- Persistent UI state (last active section)
"""

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer

from monokl import __version__
from monokl import get_logger
from monokl.config import get_config
from monokl.db.connection import get_db_manager
from monokl.db.preferences import PreferencesManager
from monokl.ui.sections import CodeReviewSection
from monokl.ui.sections import PieceOfWorkSection
from monokl.ui.sections import SectionClicked
from monokl.ui.topbar import TopBar


class MainScreen(Screen):
    """Main dashboard screen with two-section layout.

    Displays merge requests (top) and work items (bottom) in a 50/50
    vertical split. Uses reactive properties to track active section
    and loading states.

    Features caching, offline mode, and non-blocking data loading.

    Example:
        app = MonoApp()
        await app.push_screen(MainScreen())
    """

    BINDINGS = [
        Binding("tab", "switch_section", "Switch Section"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit", priority=True),
    ]

    active_section: reactive[str] = reactive("mr", bindings=True)
    active_mr_subsection: reactive[str] = reactive("assigned")
    mr_loading: reactive[bool] = reactive(False)
    work_loading: reactive[bool] = reactive(False)
    mr_offline: reactive[bool] = reactive(False)
    work_offline: reactive[bool] = reactive(False)

    # CSS for the main screen layout
    DEFAULT_CSS = """
    MainScreen {
        layout: vertical;
    }

    /* Slim scrollbars throughout the app */
    * {
        scrollbar-size: 1 1;
    }

    #mr-container {
        height: 50%;
        padding: 0;
    }

    #work-container {
        height: 1fr;
        border: round $panel;
        border-title-align: left;
        border-subtitle-align: right;
        padding: 0 1;
    }

    #work-container.active {
        border: double $success;
    }

    #work-container.offline {
        border: round $warning;
    }

    .offline-indicator {
        text-style: bold;
        color: $warning;
    }

    #sections-container {
        height: 1fr;
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

    Footer {
        background: $surface-darken-2;
        color: $text;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the main screen with two sections."""
        with Vertical(id="sections-container"):
            yield TopBar(version=__version__, id="topbar")

            with Vertical(id="mr-container"):
                self.code_review_section = CodeReviewSection()
                yield self.code_review_section

            with Vertical(id="work-container"):
                self.piece_of_work_section = PieceOfWorkSection()
                yield self.piece_of_work_section

        yield Footer()

    async def on_mount(self) -> None:
        """Handle mount event - initialize database and load data.

        Flow:
        1. Initialize database
        2. Load cached data from DB immediately (for fast startup)
        3. Start background worker to fetch fresh data from CLIs
        """
        # Initialize database
        db = get_db_manager()
        await db.initialize()

        # Initialize work store and preferences
        from monokl.ui.work_store_factory import create_work_store

        config = get_config()
        self._store = create_work_store(config)
        self._prefs = PreferencesManager()
        self._source_errors: dict[str, str] = {}  # Track failed sources for UI warnings

        # Restore UI state from preferences
        await self._restore_ui_state()

        # Step 1: Load cached data from DB immediately for fast startup
        await self._load_cached_data()

        # Step 2: Start background fetch from CLIs (unless offline mode)
        if not config.offline_mode:
            self.run_worker(self._fetch_all_data_from_clis(), exclusive=True)

        # Set border titles
        self.query_one("#work-container").border_title = "[2] Work Items"

    async def _restore_ui_state(self) -> None:
        """Restore last active section and sort preferences from preferences."""
        try:
            self.active_section = await self._prefs.get_last_active_section("mr")
            self.active_mr_subsection = await self._prefs.get_last_mr_subsection("assigned")

            # Update UI to reflect restored state
            self.code_review_section.focus_section(self.active_mr_subsection)
            if self.active_section == "work":
                self.piece_of_work_section.focus_table()

            # Restore sort preferences if enabled
            config = get_config()
            if config.preserve_sort_preference:
                await self._restore_sort_preferences()
        except Exception:
            # Ignore errors restoring state
            pass

    async def _restore_sort_preferences(self) -> None:
        """Restore sort preferences for all sections."""
        sections_to_restore = [
            ("work_items", self.piece_of_work_section),
            ("cr_assigned", self.code_review_section.assigned_to_me_section),
            ("cr_opened", self.code_review_section.opened_by_me_section),
        ]

        for section_id, section in sections_to_restore:
            sort_dict = await self._prefs.get_sort_preference(section_id)
            if sort_dict:
                section.restore_sort_state(sort_dict)

    async def _save_ui_state(self) -> None:
        """Save current UI state to preferences."""
        try:
            await self._prefs.set_last_active_section(self.active_section)
            await self._prefs.set_last_mr_subsection(self.active_mr_subsection)

            # Save sort preferences if enabled
            config = get_config()
            if config.preserve_sort_preference:
                await self._save_sort_preferences()
        except Exception:
            # Ignore errors saving state
            pass

    async def _save_sort_preferences(self) -> None:
        """Save sort preferences for all sections."""
        sections_to_save = [
            ("work_items", self.piece_of_work_section),
            ("cr_assigned", self.code_review_section.assigned_to_me_section),
            ("cr_opened", self.code_review_section.opened_by_me_section),
        ]

        for section_id, section in sections_to_save:
            sort_dict = section.get_sort_state_dict()
            if sort_dict:
                await self._prefs.set_sort_preference(section_id, sort_dict)

    async def _load_cached_data(self) -> None:
        """Load cached data from database for immediate display.

        This provides fast startup by showing cached data immediately,
        while fresh data is fetched in the background.
        """
        logger = get_logger(__name__)
        logger.info("Loading cached data from database")

        await self._load_code_reviews_cached(logger)
        await self._load_work_items_cached(logger)

    async def _load_code_reviews_cached(self, logger) -> None:
        """Load cached code reviews and update UI."""
        try:
            await self._load_assigned_reviews(logger)
            await self._load_opened_reviews(logger)
            self.mr_offline = not await self._store.is_fresh("code_reviews")
        except Exception as e:
            logger.warning("Failed to load cached code reviews", error=str(e))

    async def _load_assigned_reviews(self, logger) -> None:
        """Load assigned reviews from cache."""
        result = await self._store.get_code_reviews("assigned")
        self.code_review_section.update_assigned_to_me(result.data)
        logger.debug(f"Loaded {len(result.data)} assigned code reviews")
        self._track_failed_sources(result)

    async def _load_opened_reviews(self, logger) -> None:
        """Load opened reviews from cache."""
        result = await self._store.get_code_reviews("opened")
        self.code_review_section.update_opened_by_me(result.data)
        logger.debug(f"Loaded {len(result.data)} opened code reviews")
        self._track_failed_sources(result)

    async def _load_work_items_cached(self, logger) -> None:
        """Load cached work items and update UI."""
        try:
            result = await self._store.get_work_items()
            self.piece_of_work_section.update_data(result.data)
            logger.debug(f"Loaded {len(result.data)} work items")
            self._track_failed_sources(result)
            self.work_offline = not await self._store.is_fresh("work_items")
            self._update_work_subtitle()
        except Exception as e:
            logger.warning("Failed to load cached work items", error=str(e))

    def _update_work_subtitle(self) -> None:
        """Update work container subtitle with adapter icons."""
        work_container = self.query_one("#work-container", Vertical)
        adapters = self.piece_of_work_section.get_adapter_info()
        if adapters:
            work_container.border_subtitle = ", ".join(f"{icon} {name}" for icon, name in adapters)
        else:
            work_container.border_subtitle = ""

    def _track_failed_sources(self, result) -> None:
        """Track failed sources for UI warnings."""
        for source in result.failed_sources:
            self._source_errors[source] = result.errors.get(source, "Unknown error")

    async def _fetch_all_data_from_clis(self) -> None:
        """Fetch fresh data from CLI sources in the background.

        Uses asyncio.gather() to run fetches in parallel.
        Updates the UI with fresh data when complete.
        """
        logger = get_logger(__name__)
        logger.info("Starting background fetch from CLI sources")

        await asyncio.gather(
            self.fetch_code_reviews(),
            self.fetch_work_items(),
            return_exceptions=True,
        )

        logger.info("Background fetch from CLI sources complete")

    async def fetch_code_reviews(self) -> None:
        """Fetch fresh code reviews from all registered CLI sources.

        This method fetches fresh data from CLI sources and updates the UI.
        Cached data is loaded separately in _load_cached_data() for fast startup.
        Falls back to stale cache if API fails.
        """
        fetch_logger = get_logger(__name__)

        config = get_config()

        # Skip if offline mode is enabled
        if config.offline_mode:
            fetch_logger.info("Offline mode enabled, skipping CLI fetch for code reviews")
            return

        # Fetch fresh data from CLIs
        self.mr_loading = True
        self.code_review_section.show_loading("Fetching code reviews...")

        try:
            # Fetch assigned reviews with force_refresh
            result_assigned = await self._store.get_code_reviews("assigned", force_refresh=True)
            self.code_review_section.update_assigned_to_me(result_assigned.data)

            # Track failed sources for UI
            if result_assigned.failed_sources:
                for source in result_assigned.failed_sources:
                    self._source_errors[source] = result_assigned.errors.get(
                        source, "Unknown error"
                    )

            # Fetch opened reviews with force_refresh
            result_opened = await self._store.get_code_reviews("opened", force_refresh=True)
            self.code_review_section.update_opened_by_me(result_opened.data)

            # Track failed sources
            if result_opened.failed_sources:
                for source in result_opened.failed_sources:
                    self._source_errors[source] = result_opened.errors.get(source, "Unknown error")

            # Mark as online (not offline) if we got fresh data
            self.mr_offline = not (result_assigned.fresh or result_opened.fresh)

            fetch_logger.info(
                "Fetched code reviews",
                assigned=len(result_assigned.data),
                opened=len(result_opened.data),
                failed_sources=result_assigned.failed_sources + result_opened.failed_sources,
            )

        except Exception as e:
            fetch_logger.error("Failed to fetch code reviews", error=str(e))
            self.code_review_section.set_error(str(e))
        finally:
            self.mr_loading = False

    async def fetch_work_items(self) -> None:
        """Fetch fresh work items from all registered CLI sources.

        This method fetches fresh data from CLI sources and updates the UI.
        Cached data is loaded separately in _load_cached_data() for fast startup.
        Falls back to stale cache if APIs fail.
        """
        fetch_logger = get_logger(__name__)

        config = get_config()

        # Skip if offline mode is enabled
        if config.offline_mode:
            fetch_logger.info("Offline mode enabled, skipping CLI fetch for work items")
            return

        # Fetch fresh data from CLIs
        self.work_loading = True
        self.piece_of_work_section.show_loading("Fetching work items...")

        try:
            # Fetch work items with force_refresh
            result = await self._store.get_work_items(force_refresh=True)

            # Update the UI
            if result.data:
                # Sort: open items first, then by display key for stability
                items = sorted(result.data, key=lambda i: (not i.is_open(), i.display_key()))
                self.piece_of_work_section.update_data(items)
            else:
                self.piece_of_work_section.set_error("No work items found")

            # Track failed sources for UI
            if result.failed_sources:
                for source in result.failed_sources:
                    self._source_errors[source] = result.errors.get(source, "Unknown error")

            # Mark as online (not offline) if we got fresh data
            self.work_offline = not result.fresh
            self._update_work_subtitle()

            fetch_logger.info(
                "Fetched work items",
                count=len(result.data),
                failed_sources=result.failed_sources,
            )

        except Exception as e:
            fetch_logger.error("Failed to fetch work items", error=str(e))
            self.piece_of_work_section.set_error(str(e))
        finally:
            self.work_loading = False

    def watch_active_section(self) -> None:
        """Update visual indicators when active section changes."""
        work_container = self.query_one("#work-container", Vertical)
        assigned_section = self.code_review_section.assigned_to_me_section
        opened_section = self.code_review_section.opened_by_me_section

        assigned_section.remove_class("active")
        opened_section.remove_class("active")
        work_container.remove_class("active")

        if self.active_section == "mr":
            if self.active_mr_subsection == "assigned":
                assigned_section.add_class("active")
            else:
                opened_section.add_class("active")
        else:
            work_container.add_class("active")

        # Save UI state
        self.run_worker(self._save_ui_state(), exclusive=True)

    def watch_active_mr_subsection(self) -> None:
        """Update visual indicators when MR subsection changes."""
        if self.active_section != "mr":
            return

        assigned_section = self.code_review_section.assigned_to_me_section
        opened_section = self.code_review_section.opened_by_me_section

        assigned_section.remove_class("active")
        opened_section.remove_class("active")

        if self.active_mr_subsection == "assigned":
            assigned_section.add_class("active")
        else:
            opened_section.add_class("active")

    def watch_mr_offline(self) -> None:
        """Update visual indicator for offline/cached data."""
        assigned_section = self.code_review_section.assigned_to_me_section
        opened_section = self.code_review_section.opened_by_me_section

        if self.mr_offline:
            assigned_section.add_class("offline")
            opened_section.add_class("offline")
        else:
            assigned_section.remove_class("offline")
            opened_section.remove_class("offline")

    def watch_work_offline(self) -> None:
        """Update visual indicator for offline/cached data."""
        work_container = self.query_one("#work-container", Vertical)

        if self.work_offline:
            work_container.add_class("offline")
            work_container.border_title = "[2] Work Items (offline)"
        else:
            work_container.remove_class("offline")
            work_container.border_title = "[2] Work Items"

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
                self.code_review_section.focus_section("opened")
            else:
                self.active_section = "work"
                self.piece_of_work_section.focus_table()
        else:
            # From Work section, go back to MR "Assigned to me"
            self.active_section = "mr"
            self.active_mr_subsection = "assigned"
            self.code_review_section.focus_section("assigned")

    def action_switch_section(self) -> None:
        """Action handler for switching sections."""
        self.switch_section()

    def on_section_clicked(self, event: SectionClicked) -> None:
        """Handle section click to update active section state."""
        self.active_section = event.section_type
        if event.section_type == "mr" and event.subsection:
            self.active_mr_subsection = event.subsection

    def action_refresh(self) -> None:
        """Action handler to manually refresh data.

        Invalidates the cache for the current section and fetches fresh data.
        """
        if self.active_section == "mr":
            self.run_worker(self._refresh_merge_requests(), exclusive=True)
        else:
            self.run_worker(self._refresh_work_items(), exclusive=True)

    async def _refresh_merge_requests(self) -> None:
        """Refresh merge requests (invalidate cache first)."""
        await self._store.invalidate(data_type="code_reviews")
        await self.fetch_code_reviews()

    async def _refresh_work_items(self) -> None:
        """Refresh work items (invalidate cache first)."""
        await self._store.invalidate(data_type="work_items")
        await self.fetch_work_items()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def on_key(self, event) -> None:
        """Handle key events for navigation.

        This method handles key events directly for cases where
        the standard BINDINGS mechanism needs supplementary handling.
        Currently delegates to action handlers for consistency.

        Args:
            event: The key event from Textual.
        """
