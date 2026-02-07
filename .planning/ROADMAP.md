# Roadmap: Mono CLI

## Overview

This roadmap delivers a unified terminal dashboard that aggregates work items and pull/merge requests from Jira, GitLab (and future GitHub) into a single view. We start with foundational async infrastructure and data models, build CLI adapters that auto-detect and wrap existing authenticated tools, and finish with a responsive Textual-based dashboard with keyboard navigation. The architecture prioritizes testability (business logic before UI) and non-blocking async operations throughout.

## Phases

- [x] **Phase 1: Foundation** - Async infrastructure and data models ✓
- [ ] **Phase 2: CLI Adapters** - Auto-detection and data fetching from platform CLIs
- [ ] **Phase 3: Dashboard UI** - Textual widgets, navigation, and browser integration

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
- [ ] 02-01-PLAN.md — CLI detection mechanism and base adapter enhancements
- [ ] 02-02-PLAN.md — GitLab glab adapter with MR fetching
- [ ] 02-03-PLAN.md — Jira acli adapter with work item fetching

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

**Plans:** TBD

Plans:
- [ ] 03-01: Create DataTable widgets for PR/MR and Issue sections
- [ ] 03-02: Build main screen layout with two-section composition
- [ ] 03-03: Implement keyboard navigation and 'o' key browser integration

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | ✓ Complete | 2025-02-07 |
| 2. CLI Adapters | 0/3 | Not started | - |
| 3. Dashboard UI | 0/3 | Not started | - |

---
*Last updated: 2025-02-07 after Phase 1 completion*
