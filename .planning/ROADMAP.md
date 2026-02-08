# Roadmap: Mono CLI

## Overview

This roadmap delivers a unified terminal dashboard that aggregates work items and pull/merge requests from Jira, GitLab (and future GitHub) into a single view. We start with foundational async infrastructure and data models, build CLI adapters that auto-detect and wrap existing authenticated tools, and finish with a responsive Textual-based dashboard with keyboard navigation. The architecture prioritizes testability (business logic before UI) and non-blocking async operations throughout.

## Phases

- [x] **Phase 1: Foundation** - Async infrastructure and data models ✓
- [x] **Phase 2: CLI Adapters** - Auto-detection and data fetching from platform CLIs ✓
- [x] **Phase 3: Dashboard UI** - Textual widgets, navigation, and browser integration ✓
- [ ] **Phase 4: Add Logging with Structlog** - Add proper logging infrastructure

## Phase Details

### Phase 1: Foundation

**Goal:** Solid async infrastructure and validated data models that can parse CLI outputs without blocking

**Depends on:** Nothing (first phase)

**Requirements:** DATA-03, ASYNC-01, ASYNC-02, ASYNC-03, ASYNC-04, TEST-01

**Success Criteria** (what must be TRUE):
1. Async subprocess calls complete without blocking the main thread
2. Workers use exclusive=True to prevent race conditions when multiple fetches run
3. Pydantic models validate and parse JSON from gh/glab/acli CLI outputs
4. Failed CLI calls raise exceptions with descriptive error messages (no silent failures)
5. Unit tests exist for all Pydantic models with valid and invalid input cases

**Plans:** 3 plans in 3 waves

Plans:
- [x] 01-01-PLAN.md — UV project init, Ruff/MyPy/pytest setup, directory structure
- [x] 01-02-PLAN.md — Pydantic models for MR/PR and Issue data structures
- [x] 01-03-PLAN.md — Async subprocess utilities with Textual Workers API, error handling

### Phase 2: CLI Adapters

**Goal:** Detect installed CLIs and fetch real data from GitLab and Jira with proper authentication handling

**Depends on:** Phase 1

**Requirements:** DASH-04, DATA-01, DATA-02, DATA-04, DATA-05, CONFIG-01, CONFIG-02, TEST-02

**Success Criteria** (what must be TRUE):
1. Application detects presence of glab and acli CLIs on startup
2. GitLab MRs are fetched via glab --json and include: MR number, title, status, author, URL
3. Jira work items are fetched via acli --json and include: issue key, title, status, priority, URL
4. Unauthenticated or missing CLIs result in hidden sections (no crashes, no prompts)
5. All CLI calls use existing authentication (no separate auth flow in the app)
6. Async tests verify each CLI adapter handles success, auth failure, and network errors

**Plans:** 3 plans in 2 waves

Plans:
- [x] 02-01-PLAN.md — CLI detection mechanism and base adapter enhancements
- [x] 02-02-PLAN.md — GitLab glab adapter with MR fetching
- [x] 02-03-PLAN.md — Jira acli adapter with work item fetching

### Phase 3: Dashboard UI

**Goal:** A responsive two-section dashboard with keyboard navigation and browser integration

**Depends on:** Phase 2

**Requirements:** DASH-01, DASH-02, DASH-03, DASH-05, DATA-06, TEST-03

**Success Criteria** (what must be TRUE):
1. Dashboard renders with two sections: PRs/MRs on top, Work Items below
2. Each section shows a loading spinner while fetching data
3. User can navigate items with j/k or arrow keys within each section
4. User can press 'o' to open the selected item in their default browser
5. Each item displays: Key + Title + Status + Priority in a consistent format
6. UI remains responsive during data fetching (no freezing)
7. Integration tests verify widget behavior using Textual's Pilot class

**Plans:** 5 plans in 3 waves (3 original + 2 gap closure)

Plans:
- [x] 03-01-PLAN.md — Create DataTable section widgets (MergeRequestSection, WorkItemSection)
- [x] 03-02-PLAN.md — Build main screen with 50/50 layout and async data fetching
- [x] 03-03-PLAN.md — Implement keyboard navigation and browser integration
- [x] 03-04-PLAN.md — Fix Textual workers API (replace deprecated @work decorator)
- [x] 03-05-PLAN.md — Fix acli auth check command (replace invalid whoami command)

### Phase 4: Add Logging with Structlog

**Goal:** Add proper logging infrastructure to the application for debugging and monitoring

**Depends on:** Phase 3

**Requirements:** LOG-01, LOG-02

**Success Criteria** (what must be TRUE):
1. Application uses structlog for structured logging
2. Logs are written to both console and file
3. Log level is configurable
4. Sensitive data is not logged
5. Debug mode flag enables verbose logging

**Plans:** 1 plan in 1 wave

Plans:
- [ ] 04-01-PLAN.md — Set up structlog for structured logging with console/file output

**Details:**
[To be added during planning]

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | ✓ Complete | 2025-02-07 |
| 2. CLI Adapters | 3/3 | ✓ Complete | 2026-02-07 |
| 3. Dashboard UI | 5/5 | ✓ Complete | 2026-02-08 |
| 4. Add Logging | 0/1 | Planned | - |

---
*Last updated: 2026-02-07 after 02-03 completion (Phase 2 complete)*
