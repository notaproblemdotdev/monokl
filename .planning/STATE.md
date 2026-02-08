# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2025-02-07)

**Core value:** One dashboard showing all assigned work items and pending PRs/MRs without switching between browser tabs or context switching between platforms.
**Current focus:** Phase 2 - CLI Adapters

## Current Position

Phase: 3 of 3 (Dashboard UI)
Plan: 4 of 4 in current phase (Gap Closure)
Status: Phase complete
Last activity: 2026-02-08 — Completed 03-05-PLAN.md (Fix acli Auth Check Command)

Progress: [██████████] 100% (10 of 10 total plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 4.0 min
- Total execution time: 0.46 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation | 3/3 | 12m 33s | 4m 11s |
| 2. CLI Adapters | 3/3 | 14m 0s | 4m 40s |
| 3. Dashboard UI | 4/4 | 12m 0s | 3m 0s |

**Recent Trend:**
- Last 5 plans: 03-02 (3m), 03-03 (3m), 03-05 (2m)
- Trend: Gap closure complete - acli auth fixed!

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Initialization: Use Textual framework for TUI (modern async support)
- Initialization: Shell out to existing CLIs vs APIs (reuse existing auth)
- Initialization: UV for dependency management, Ruff for linting, MyPy for type checking

**New from 01-01:**
- Use src/ layout for better package isolation and testing
- Configure Ruff with comprehensive lint rules (E, F, I, N, W, UP, B, C4, SIM)
- Enable strict MyPy type checking for early error detection
- Use pytest-asyncio for testing async code in future phases

**New from 01-02:**
- Use BeforeValidator for datetime parsing from ISO 8601 JSON strings
- Standardize helper interface: display_key(), display_status(), is_open() on all models
- Pattern validation with regex for Jira keys (PROJECT-123 format)
- Strict mode with ConfigDict for early type error detection

**New from 01-03:**
- Use asyncio.create_subprocess_exec over subprocess.run for true async execution
- Implement @work(exclusive=True) pattern to prevent data fetching race conditions
- Create CLIAdapter base class for consistent CLI interface across platforms
- Use TypeVar for generic model parsing in fetch_and_parse()
- Cache CLI availability check in adapter to avoid repeated which() calls

**New from 02-01:**
- Use TypedDict for DetectionResult to provide clear field names and type safety
- Cache detection results at registry level after first detect_all() call
- Use lightweight auth check commands (e.g., "auth status") rather than data fetching
- Return copies of cached results to prevent external mutation
- Clear cache when new detector registered to ensure freshness
- Registry pattern: register detectors, detect_all returns all results, query methods filter

**New from 02-02:**
- CLI Adapter pattern: Inherit from CLIAdapter, implement fetch_* and check_auth methods
- glab mr list --json with --author and --state filters for targeted fetching
- check_auth() returns boolean (not exception) for detection flow compatibility
- Mock asyncio.create_subprocess_exec for async CLI testing

**New from 02-03:**
- acli whoami for lightweight Jira auth checking
- acli jira issue list --json with --assignee and --status filters
- Bug fix: Add 'not authenticated' to CLIAuthError.AUTH_PATTERNS
- Jira API URL to browser URL transformation in model property

**New from 03-01:**
- Textual reactive properties for data binding in widgets
- SectionState enum for explicit UI state management (LOADING, EMPTY, ERROR, DATA)
- Base class pattern for shared section functionality
- DataTable with zebra_stripes for readability
- Row keys for storing item URLs (for browser integration)
- Title truncation with ellipsis (40 char limit)
- Pilot API with TestApp wrapper for widget testing

**New from 03-02:**
- Nested @work decorator pattern for fire-and-forget async workers
- DetectionRegistry with CLIDetector instances for CLI availability checking
- Reactive active_section property with CSS border highlight
- Fire-and-forget workers with `_ = worker_func()` to silence warnings
- MainScreen.compose() stores section references as instance attributes
- Error handling per section (CLI not found, not authenticated, network errors)

**New from 03-03:**
- Textual BINDINGS with action_* methods for keyboard navigation
- Tab key switches active section with CSS border highlighting
- j/k and arrow keys navigate items within focused section
- 'o' key opens selected item URL in default browser via webbrowser module
- Section-scoped selection (each DataTable maintains independent cursor)
- Row keys store URLs for reliable lookup in get_selected_url()
- on_key() handler for custom key event processing
- Pilot API for integration testing keyboard navigation
- Silent error handling for browser open failures

**New from 03-04 (Gap Closure - Workers API):**
- Migrated from deprecated @work decorator to Textual 7.x run_worker() API
- self.run_worker(self.fetch_method(), exclusive=True) replaces @work(exclusive=True)
- Workers now properly execute and resolve loading spinners to data/empty/error states
- Textual 7.x compatibility achieved, no deprecated APIs used

**New from 03-05 (Gap Closure - Auth Command):**
- acli jira auth status is the correct command for auth checking
- acli whoami doesn't exist and was causing auth check failures
- Consistent auth command between JiraAdapter and CLIDetector

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-08T17:43:44Z
Stopped at: Completed 03-04-PLAN.md (Gap Closure - Workers API)
Resume file: None

## Next Phase

Phase 3: Dashboard UI - **COMPLETE**
- All 4 plans completed (03-01: Sections, 03-02: MainScreen, 03-03: Navigation, 03-05: Gap Closure)
- v1 requirements fully implemented
- Dashboard displays merge requests and work items
- Full keyboard navigation: Tab switching, j/k arrows, 'o' for browser
- Auto-detection of CLIs with graceful error handling
- Comprehensive test coverage with pytest and Pilot API
- Gap closure: Fixed acli auth check command

**Project v1 is feature complete!**

Next steps could include:
- v2 features: refresh (r/F5), search/filter (/), help (?), GitHub support
- Manual testing with real CLIs
- Documentation improvements
- Packaging and distribution
