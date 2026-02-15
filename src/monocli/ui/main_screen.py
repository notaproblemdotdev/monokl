"""Main screen for the Mono CLI dashboard.

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
import webbrowser
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Label

from monocli import __version__, get_logger
from monocli.adapters.jira import JiraAdapter
from monocli.adapters.todoist import TodoistAdapter
from monocli.config import ConfigError, get_config
from monocli.db.cache import CacheManager
from monocli.db.connection import get_db_manager
from monocli.db.preferences import PreferencesManager
from monocli.models import CodeReview, WorkItem
from monocli.sources import (
    CodeReviewSource,
    GitHubSource,
    GitLabCodeReviewSource,
    SourceRegistry,
)
from monocli.ui.sections import CodeReviewSection, PieceOfWorkSection
from monocli.ui.topbar import TopBar

if TYPE_CHECKING:
    pass


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

    # Key bindings
    BINDINGS = [
        ("tab", "switch_section", "Switch Section"),
        ("o", "open_selected", "Open in Browser"),
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    # Reactive state
    active_section: reactive[str] = reactive("mr")  # "mr" or "work"
    active_mr_subsection: reactive[str] = reactive("assigned")  # "assigned" or "opened"
    mr_loading: reactive[bool] = reactive(False)
    work_loading: reactive[bool] = reactive(False)
    mr_offline: reactive[bool] = reactive(False)  # Shows cached data
    work_offline: reactive[bool] = reactive(False)  # Shows cached data

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

    #mr-container.offline {
        border: solid $warning;
    }

    #work-container.offline {
        border: solid $warning;
    }

    .section-label {
        text-style: bold;
        padding: 0;
        margin: 0 0 1 0;
        height: auto;
        text-align: center;
    }

    .offline-indicator {
        text-style: bold;
        color: $warning;
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
            # App title above the code reviews section
            yield TopBar(version=__version__, id="topbar")

            # Top section: Code Reviews (with two subsections)
            with Vertical(id="mr-container"):
                yield Label("Code Reviews", classes="section-label")
                self.code_review_section = CodeReviewSection()
                yield self.code_review_section

            # Bottom section: Work Items
            with Vertical(id="work-container"):
                self.piece_of_work_section = PieceOfWorkSection()
                yield self.piece_of_work_section

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

        # Initialize cache and preferences
        config = get_config()
        self._cache = CacheManager(ttl_seconds=config.cache_ttl)
        self._prefs = PreferencesManager()

        # Restore UI state from preferences
        await self._restore_ui_state()

        # Step 1: Load cached data from DB immediately for fast startup
        await self._load_cached_data()

        # Step 2: Start background fetch from CLIs (unless offline mode)
        if not config.offline_mode:
            self.run_worker(self._fetch_all_data_from_clis(), exclusive=True)

    async def _restore_ui_state(self) -> None:
        """Restore last active section from preferences."""
        try:
            self.active_section = await self._prefs.get_last_active_section("mr")
            self.active_mr_subsection = await self._prefs.get_last_mr_subsection("assigned")

            # Update UI to reflect restored state
            self.code_review_section.focus_section(self.active_mr_subsection)
            if self.active_section == "work":
                self.piece_of_work_section.focus_table()
        except Exception:
            # Ignore errors restoring state
            pass

    async def _save_ui_state(self) -> None:
        """Save current UI state to preferences."""
        try:
            await self._prefs.set_last_active_section(self.active_section)
            await self._prefs.set_last_mr_subsection(self.active_mr_subsection)
        except Exception:
            # Ignore errors saving state
            pass

    async def _load_cached_data(self) -> None:
        """Load cached data from database for immediate display.

        This provides fast startup by showing cached data immediately,
        while fresh data is fetched in the background.
        """
        logger = get_logger(__name__)
        logger.info("Loading cached data from database")

        # Load cached merge requests
        try:
            cached_assigned = await self._cache.get_merge_requests("assigned", accept_stale=True)
            cached_opened = await self._cache.get_merge_requests("opened", accept_stale=True)

            if cached_assigned:
                code_reviews_assigned = [
                    self._convert_mr_to_code_review(mr) for mr in cached_assigned
                ]
                self.code_review_section.update_assigned_to_me(code_reviews_assigned)
                logger.debug(f"Loaded {len(cached_assigned)} assigned MRs from cache")

            if cached_opened:
                code_reviews_opened = [self._convert_mr_to_code_review(mr) for mr in cached_opened]
                self.code_review_section.update_opened_by_me(code_reviews_opened)
                logger.debug(f"Loaded {len(cached_opened)} opened MRs from cache")

            # Check if cache is fresh
            is_fresh = await self._cache.is_cache_valid("merge_requests")
            self.mr_offline = not is_fresh

            if not cached_assigned and not cached_opened:
                logger.debug("No cached merge requests found")

        except Exception as e:
            logger.warning("Failed to load cached merge requests", error=str(e))

        # Load cached work items
        try:
            cached_items = await self._cache.get_work_items(accept_stale=True)

            if cached_items:
                self.piece_of_work_section.update_data(cached_items)
                logger.debug(f"Loaded {len(cached_items)} work items from cache")

                # Check if cache is fresh
                is_fresh = await self._cache.is_cache_valid("work_items")
                self.work_offline = not is_fresh
            else:
                logger.debug("No cached work items found")

        except Exception as e:
            logger.warning("Failed to load cached work items", error=str(e))

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

    def _convert_mr_to_code_review(self, mr):
        """Convert a MergeRequest model to a CodeReview model."""
        author = mr.author.get("name") or mr.author.get("username") or "Unknown"
        return CodeReview(
            id=str(mr.iid),
            key=mr.display_key(),
            title=mr.title,
            state="open" if mr.state == "opened" else mr.state,
            author=author,
            source_branch=mr.source_branch,
            url=str(mr.web_url),
            created_at=mr.created_at,
            draft=mr.draft,
            adapter_type="gitlab",
            adapter_icon="🦊",
        )

    async def fetch_code_reviews(self) -> None:
        """Fetch fresh code reviews from all registered CLI sources.

        This method fetches fresh data from CLI sources and updates the UI.
        Cached data is loaded separately in _load_cached_data() for fast startup.
        Falls back to stale cache if API fails.
        """
        logger = get_logger(__name__)

        config = get_config()

        # Skip if offline mode is enabled
        if config.offline_mode:
            logger.info("Offline mode enabled, skipping CLI fetch for code reviews")
            return

        try:
            gitlab_source_args: dict[str, Any] = {"group": get_config().require_gitlab_group()}
            gitlab_source_mapping: dict[type[GitLabCodeReviewSource], dict[str, Any] | None] = {
                GitLabCodeReviewSource: gitlab_source_args
            }
        except ConfigError:
            logger.warning("GitLab group not configured, skipping GitLab source")
            gitlab_source_mapping = {}

        code_review_sources_mapping: dict[type[CodeReviewSource], dict[str, Any] | None] = {
            GitHubSource: None,
            **gitlab_source_mapping,
        }

        registry = SourceRegistry()

        for source_cls, init_args in code_review_sources_mapping.items():
            try:
                source = source_cls(**init_args) if init_args is not None else source_cls()
                registry.register_code_review_source(source)
            except Exception as e:
                logger.warning(f"Failed to initialize source {source_cls.__name__}", error=str(e))

        # Fetch fresh data from CLIs
        self.mr_loading = True
        self.code_review_section.show_loading("Fetching code reviews...")

        try:
            # Fetch from all sources
            results = await registry.fetch_all_code_reviews(
                include_assigned=True,
                include_authored=True,
                include_pending_review=True,
            )

            # Combine results from all sources
            all_assigned: list = []
            all_authored: list = []

            for source_type, reviews in results.items():
                for review in reviews:
                    # Separate into assigned and authored
                    # (for now, put everything in assigned)
                    all_assigned.append(review)

            # Deduplicate by URL
            seen_urls = set()
            deduped_assigned = []
            for review in all_assigned:
                if review.url not in seen_urls:
                    seen_urls.add(review.url)
                    deduped_assigned.append(review)

            # Update sections
            self.code_review_section.update_assigned_to_me(deduped_assigned)
            self.code_review_section.update_opened_by_me(all_authored)

            # Cache the fresh data
            await self._cache.set_merge_requests("assigned", deduped_assigned)
            await self._cache.set_merge_requests("opened", all_authored)

            # Mark as online (not offline)
            self.mr_offline = False

        except Exception as e:
            logger.error("Failed to fetch code reviews", error=str(e))

            # Try to use stale cache as fallback
            cached_assigned = await self._cache.get_merge_requests("assigned", accept_stale=True)
            cached_opened = await self._cache.get_merge_requests("opened", accept_stale=True)

            if cached_assigned or cached_opened:
                if cached_assigned:
                    code_reviews_assigned = [
                        self._convert_mr_to_code_review(mr) for mr in cached_assigned
                    ]
                    self.code_review_section.update_assigned_to_me(code_reviews_assigned)
                if cached_opened:
                    code_reviews_opened = [
                        self._convert_mr_to_code_review(mr) for mr in cached_opened
                    ]
                    self.code_review_section.update_opened_by_me(code_reviews_opened)
                self.mr_offline = True
            else:
                self.code_review_section.set_error(str(e))
        finally:
            self.mr_loading = False

    async def fetch_work_items(self) -> None:
        """Fetch fresh work items from Jira and Todoist CLI sources.

        This method fetches fresh data from CLI sources and updates the UI.
        Cached data is loaded separately in _load_cached_data() for fast startup.
        Falls back to stale cache if APIs fail.
        """

        logger = get_logger(__name__)

        config = get_config()

        # Skip if offline mode is enabled
        if config.offline_mode:
            logger.info("Offline mode enabled, skipping CLI fetch for work items")
            return

        items: list[WorkItem] = []

        # Fetch fresh data from CLIs
        self.work_loading = True
        self.piece_of_work_section.show_loading("Fetching work items...")

        # Fetch from Jira
        jira_items = []
        try:
            jira_adapter = JiraAdapter()
            if jira_adapter.is_available() and await jira_adapter.check_auth():
                jira_items = await jira_adapter.fetch_assigned_items()
                items.extend(jira_items)
        except Exception as e:
            logger.warning("Jira fetch failed", exc_info=e)
            await self._cache.record_error("work_items", f"Jira: {e}")

        # Fetch from Todoist
        todoist_items = []
        try:
            if config.todoist_token:
                todoist_adapter = TodoistAdapter(config.todoist_token)
                if await todoist_adapter.check_auth():
                    todoist_tasks = await todoist_adapter.fetch_tasks(
                        project_names=config.todoist_projects or None,
                        show_completed=config.todoist_show_completed,
                        show_completed_for_last=config.todoist_show_completed_for_last,
                    )
                    todoist_items.extend(todoist_tasks)
                    items.extend(todoist_tasks)
        except ImportError:
            logger.debug("todoist-api-python not installed, skipping Todoist")
        except Exception as e:
            logger.warning("Todoist fetch failed", exc_info=e)
            await self._cache.record_error("work_items", f"Todoist: {e}")

        if items:
            # Sort: open items first, then by display key for stability
            items.sort(key=lambda i: (not i.is_open(), i.display_key()))
            self.piece_of_work_section.update_data(items)

            # Cache the fresh data
            await self._cache.set_work_items(items)

            # Mark as online
            self.work_offline = False
        else:
            # No items fetched - try stale cache
            cached_items = await self._cache.get_work_items(accept_stale=True)

            if cached_items:
                self.piece_of_work_section.update_data(cached_items)
                self.work_offline = True
            else:
                self.piece_of_work_section.set_error("No work item sources available")

        self.work_loading = False

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

        # Save UI state
        self.run_worker(self._save_ui_state(), exclusive=True)

    def watch_mr_offline(self) -> None:
        """Update visual indicator for offline/cached data."""
        mr_container = self.query_one("#mr-container", Vertical)
        label = self.query_one("#mr-container > .section-label", Label)

        if self.mr_offline:
            mr_container.add_class("offline")
            label.update("Pull/merge requests 📴 (offline)")
        else:
            mr_container.remove_class("offline")
            label.update("Pull/merge requests")

    def watch_work_offline(self) -> None:
        """Update visual indicator for offline/cached data."""
        work_container = self.query_one("#work-container", Vertical)

        if self.work_offline:
            work_container.add_class("offline")
        else:
            work_container.remove_class("offline")

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

    def action_open_selected(self) -> None:
        """Action handler to open selected item in browser.

        Opens the URL of the currently selected row in the
        active section's DataTable.
        """
        url: str | None = None

        if self.active_section == "mr":
            url = self.code_review_section.get_selected_url(self.active_mr_subsection)
        else:
            url = self.piece_of_work_section.get_selected_url()

        if url:
            try:
                webbrowser.open(url)
            except Exception:
                # Log error but don't crash
                pass

    def action_refresh(self) -> None:
        """Action handler to manually refresh data.

        Invalidates the cache for the current section and fetches fresh data.
        """
        if self.active_section == "mr":
            # Invalidate MR cache and refresh
            self.run_worker(self._refresh_merge_requests(), exclusive=True)
        else:
            # Invalidate work items cache and refresh
            self.run_worker(self._refresh_work_items(), exclusive=True)

    async def _refresh_merge_requests(self) -> None:
        """Refresh merge requests (invalidate cache first)."""
        await self._cache.invalidate("merge_requests")
        await self.fetch_code_reviews()

    async def _refresh_work_items(self) -> None:
        """Refresh work items (invalidate cache first)."""
        await self._cache.invalidate("work_items")
        await self.fetch_work_items()

    def action_move_down(self) -> None:
        """Action handler to move selection down."""
        if self.active_section == "mr":
            self.code_review_section.select_next(self.active_mr_subsection)
        else:
            self.piece_of_work_section.select_next()

    def action_move_up(self) -> None:
        """Action handler to move selection up."""
        if self.active_section == "mr":
            self.code_review_section.select_previous(self.active_mr_subsection)
        else:
            self.piece_of_work_section.select_previous()

    def action_quit(self) -> None:
        """Quit the application."""
        # Save UI state before quitting
        self.run_worker(self._save_ui_state(), exclusive=True)
        self.app.exit()

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
