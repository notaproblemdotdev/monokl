---
phase: 01-foundation
plan: 02
subsystem: data-models
tags: [pydantic, validation, models, pytest]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Project structure with UV, Ruff, MyPy, pytest (from 01-01)
provides:
  - Pydantic v2 models for GitHub PRs, GitLab MRs, GitHub Issues, Jira work items
  - Enums for WorkItemStatus and Priority
  - ISO 8601 datetime parsing with BeforeValidator
  - Helper methods for display formatting
  - Comprehensive test suite with 56 test cases
affects:
  - Phase 2: CLI Adapters (will use these models for parsing CLI output)
  - Phase 3: Dashboard UI (will use display_key(), is_open() for rendering)

# Tech tracking
tech-stack:
  added:
    - pydantic (already present, utilized for v2 features)
    - typing-extensions (for Annotated type hints)
  patterns:
    - BeforeValidator for datetime parsing from JSON strings
    - Strict validation with ConfigDict
    - Pattern validation with regex (Jira keys, state values)
    - Property-based computed fields (JiraWorkItem.summary, status)

key-files:
  created:
    - src/monocli/models.py
    - tests/test_models.py
  modified: []

key-decisions:
  - "Use BeforeValidator to parse ISO 8601 datetime strings from CLI JSON output"
  - "Jira keys validated with regex: ^[A-Z][A-Z0-9]*-\d+$ (project-number format)"
  - "Helper methods standardized: display_key(), display_status(), is_open()"
  - "All models use strict validation with ConfigDict(strict=True)"

patterns-established:
  - "Pydantic v2 pattern: Annotated types with BeforeValidator for data transformation"
  - "Model pattern: Common helper interface (display_key, display_status, is_open) across all work item types"
  - "Test pattern: Fixtures for valid data, parametrize for state variations"

# Metrics
duration: 4min
completed: 2026-02-07
---

# Phase 1 Plan 2: Pydantic Models for Platform Data Summary

**Pydantic v2 models with strict validation, ISO 8601 datetime parsing, and comprehensive 56-test suite covering valid and invalid input cases**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-07T18:50:48Z
- **Completed:** 2026-02-07T18:55:31Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created Pydantic v2 models for all platform data structures
- Implemented strict validation with ConfigDict and Field constraints
- Added ISO 8601 datetime parsing with BeforeValidator for CLI JSON output
- Created comprehensive test suite with 56 test cases (all passing)
- Achieved 94% test coverage on models module
- Added helper methods for consistent display formatting across all models

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Pydantic models for MR/PR data** - `b5aeb38` (feat)
2. **Task 2: Create comprehensive model tests** - `3d933b0` (test)

**Plan metadata:** [to be committed]

## Files Created/Modified

- `src/monocli/models.py` - Pydantic models for PullRequest, MergeRequest, GitHubIssue, JiraWorkItem with validation
- `tests/test_models.py` - 56 comprehensive tests covering valid/invalid inputs, helper methods, and edge cases

## Decisions Made

- **Use BeforeValidator for datetime parsing** - CLI JSON output provides ISO 8601 strings; BeforeValidator converts them to datetime objects automatically
- **Jira key pattern validation** - Keys must match `[A-Z][A-Z0-9]*-\d+$` (e.g., PROJ-123) for project-number format
- **Standardized helper interface** - All models implement `display_key()`, `display_status()`, `is_open()` for consistent UI rendering
- **Strict mode enabled** - All models use `ConfigDict(strict=True, validate_assignment=True)` to catch type errors early

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed datetime parsing from JSON strings**

- **Found during:** Task 2 (running tests)
- **Issue:** Pydantic v2 strict mode doesn't auto-parse datetime strings; ISO 8601 strings from CLI output caused ValidationError
- **Fix:** Added `BeforeValidator(parse_datetime)` with `IsoDateTime` type alias; handles both 'Z' and '+00:00' suffixes
- **Files modified:** src/monocli/models.py
- **Verification:** Tests with datetime strings now pass
- **Committed in:** 3d933b0 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed type annotation for JiraWorkItem.summary property**

- **Found during:** Task 2 (mypy type checking)
- **Issue:** `self.fields.get("summary", "")` returns `Any` due to `dict[str, Any]` type
- **Fix:** Added explicit `str()` conversion with null check
- **Files modified:** src/monocli/models.py
- **Verification:** mypy passes with no errors
- **Committed in:** 3d933b0 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

None - tests and type checking pass after auto-fixes.

## Next Phase Readiness

- Models are ready for CLI adapter implementation in Phase 2
- All models can parse JSON output from gh, glab, and acli CLIs
- Validation ensures malformed data raises clear errors
- Test patterns established for future model additions

---

*Phase: 01-foundation*
*Completed: 2026-02-07*

## Self-Check: PASSED

All verification checks passed:
- src/monocli/models.py: FOUND
- tests/test_models.py: FOUND
- All commits verified: b5aeb38, 3d933b0, 2e1cb93
