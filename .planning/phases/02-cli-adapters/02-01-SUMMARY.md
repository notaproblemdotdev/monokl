---
phase: 02-cli-adapters
plan: 01
subsystem: cli
tags: [asyncio, detection, glab, acli, shutil, subprocess]

requires:
  - phase: 01-foundation
    provides: Async subprocess utilities (run_cli_command), exceptions (CLIAuthError, CLINotFoundError)

provides:
  - CLIDetector class for checking CLI installation and auth status
  - DetectionRegistry class for managing multiple CLI detectors
  - DetectionResult TypedDict for structured detection results
  - Concurrent detection using asyncio.gather
  - Result caching to avoid repeated system calls
  - Query methods (get_available, is_available) for availability checks

affects:
  - 02-02 (GitLab glab adapter - will use detection to check glab availability)
  - 02-03 (Jira acli adapter - will use detection to check acli availability)
  - 03-01 (Dashboard UI - will use detection to hide sections for unavailable CLIs)

tech-stack:
  added: []
  patterns:
    - "Concurrent async operations with asyncio.gather"
    - "TypedDict for structured return types"
    - "Cache invalidation on state change (register clears cache)"

key-files:
  created:
    - src/monocli/adapters/__init__.py - Package exports
    - src/monocli/adapters/detection.py - Core detection logic
    - tests/test_detection.py - Comprehensive test suite
  modified: []

key-decisions:
  - "Use TypedDict for DetectionResult to provide clear field names and type safety"
  - "Cache results at registry level after first detect_all() call"
  - "Use lightweight auth check commands (e.g., 'auth status') rather than data fetching"
  - "Return copy of cached results to prevent external mutation"
  - "Clear cache when new detector registered to ensure freshness"

patterns-established:
  - "CLIDetector pattern: check installation with shutil.which, validate auth with trial command"
  - "Registry pattern: register detectors, detect_all returns all results, query methods filter"
  - "Caching pattern: cache results after first detection, provide clear_cache() for testing"

duration: 8 min
completed: 2026-02-07
---

# Phase 2 Plan 1: CLI Detection Mechanism Summary

**Unified CLI detection with concurrent checks, caching, and registry pattern for discovering available CLIs (glab, acli) and their authentication status**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-07T19:42:19Z
- **Completed:** 2026-02-07T19:50:19Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created CLIDetector class that checks CLI installation via shutil.which() and validates authentication via trial commands
- Built DetectionRegistry for managing multiple CLI detectors with concurrent execution via asyncio.gather
- Implemented result caching to avoid repeated system calls
- Added query methods (get_available(), is_available()) for checking CLI readiness
- Created comprehensive test suite with 21 tests covering all edge cases
- Achieved 97% test coverage on detection module

## Task Commits

Each task was committed atomically:

1. **Task 1: Create adapter package structure and detection module** - `8c9b3b7` (feat)
2. **Task 2: Write comprehensive tests for detection functionality** - `2fdf1e0` (test)

**Plan metadata:** `TBD` (docs: complete plan)

## Files Created/Modified

- `src/monocli/adapters/__init__.py` - Package exports for CLIDetector, DetectionRegistry, DetectionResult
- `src/monocli/adapters/detection.py` - Core detection logic with 284 lines
- `tests/test_detection.py` - Comprehensive test suite with 21 tests

## Decisions Made

- Used TypedDict for DetectionResult to provide clear field names and type safety while keeping it a simple dictionary
- Implemented caching at registry level to avoid repeated subprocess calls (performance optimization)
- Used lightweight auth check commands (e.g., "auth status") rather than fetching actual data
- Return copies of cached results to prevent external mutation
- Clear cache automatically when new detector registered to ensure freshness

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Minor type checking issue with asyncio.gather return_exceptions=True pattern - resolved by explicitly typing the results list as `list[DetectionResult | BaseException]` and using isinstance check with BaseException for proper type narrowing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for 02-02 (GitLab glab adapter):
- DetectionRegistry can check if glab is available before attempting data fetch
- Pattern established for CLI adapters to use detection before operations
- Caching mechanism prevents repeated system calls during app lifecycle

Ready for 02-03 (Jira acli adapter):
- Same detection pattern applies to acli CLI
- Can register multiple detectors and run them concurrently

Ready for 03-01 (Dashboard UI):
- Registry provides get_available() to determine which sections to show/hide
- is_available() method allows quick checks for specific CLI availability

---
*Phase: 02-cli-adapters*
*Completed: 2026-02-07*
