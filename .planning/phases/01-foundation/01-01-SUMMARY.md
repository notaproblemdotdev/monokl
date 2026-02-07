---
phase: 01-foundation
plan: 01
subsystem: tooling
tags: [uv, ruff, mypy, pytest, python-3.13, src-layout]

# Dependency graph
requires: []
provides:
  - UV project configuration with pyproject.toml
  - Ruff linting and formatting setup
  - MyPy strict type checking configuration
  - pytest with asyncio and coverage
  - src/ layout package structure
  - tests/ directory structure
  - py.typed marker for PEP 561 compliance
affects:
  - 01-02 (Pydantic models)
  - 01-03 (Async subprocess utilities)

# Tech tracking
tech-stack:
  added:
    - uv (0.9.15)
    - ruff (0.15.0)
    - mypy (1.19.1)
    - pytest (9.0.2)
    - pytest-asyncio (1.3.0)
    - pytest-cov (7.0.0)
    - textual (>=7.5.0)
    - pydantic (>=2.12.5)
  patterns:
    - src/ layout for package structure
    - pyproject.toml for all tool configuration
    - Strict type checking with MyPy
    - pytest-asyncio for async test support

key-files:
  created:
    - pyproject.toml
    - src/monocli/__init__.py
    - src/monocli/py.typed
    - tests/__init__.py
    - tests/conftest.py
    - .python-version
    - uv.lock
  modified:
    - pyproject.toml (multiple times for tool configuration)

key-decisions:
  - "Use src/ layout for better package isolation and testing"
  - "Configure Ruff with comprehensive lint rules and 100 char line length"
  - "Enable strict MyPy type checking for early error detection"
  - "Use pytest-asyncio for testing async code in future phases"

patterns-established:
  - "Tool configuration centralized in pyproject.toml"
  - "Dev dependencies managed via [project.optional-dependencies]"
  - "src/monocli/ package structure with __version__ marker"

# Metrics
duration: 2m 33s
completed: 2026-02-07
---

# Phase 01 Plan 01: UV Project Initialization Summary

**Python 3.13 project initialized with UV package management, Ruff linting/formatting, MyPy strict type checking, and pytest with asyncio and coverage support**

## Performance

- **Duration:** 2m 33s
- **Started:** 2026-02-07T18:45:45Z
- **Completed:** 2026-02-07T18:48:18Z
- **Tasks:** 3 completed
- **Files created/modified:** 8

## Accomplishments

- Initialized UV project with Python 3.13 target and src/ layout
- Configured Ruff with comprehensive lint rules (E, F, I, N, W, UP, B, C4, SIM)
- Set up MyPy with strict type checking and error codes
- Configured pytest with asyncio mode and coverage reporting
- Created package structure with py.typed marker for PEP 561
- Established tests/ directory with conftest.py fixtures

## Task Commits

Each task was committed atomically:

1. **Task 1: Initialize UV project with src layout** - `1d50c55` (chore)
2. **Task 2: Configure Ruff for linting and formatting** - `c5b3052` (chore)
3. **Task 3: Configure MyPy and pytest** - `36f1afb` (chore)

**Deviation fix:** `063bf17` (refactor) - Fixed Ruff deprecation warning

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `pyproject.toml` - UV project config with dependencies, Ruff, MyPy, pytest settings
- `src/monocli/__init__.py` - Package init with __version__ = "0.1.0"
- `src/monocli/py.typed` - PEP 561 type checking marker (empty file)
- `tests/__init__.py` - Tests package marker
- `tests/conftest.py` - pytest fixtures including event_loop_policy
- `.python-version` - Python 3.13 version marker
- `uv.lock` - Locked dependency versions
- `README.md` - Project readme (auto-generated)

## Decisions Made

- Followed UV's default src/ layout for clean package isolation
- Used pyproject.toml for all tool configuration (centralized)
- Added textual and pydantic as core dependencies for future phases
- Configured Ruff with Google docstring convention for consistency
- Enabled strict MyPy checks (disallow_untyped_defs, etc.) for code quality
- Set up pytest-asyncio with auto mode for seamless async testing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed Ruff deprecation warning**

- **Found during:** Final verification
- **Issue:** Ruff emitted deprecation warning about top-level `select` and `ignore` settings
- **Fix:** Moved settings under `[tool.ruff.lint]` section
- **Files modified:** pyproject.toml
- **Verification:** `uv run ruff check src/` now passes without warnings
- **Committed in:** `063bf17`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor configuration adjustment for tool compatibility. No scope creep.

## Issues Encountered

None - all tasks completed as planned.

## User Setup Required

None - no external service configuration required.

## Verification Results

All verification criteria passed:

- ✅ `uv sync` installs all dependencies
- ✅ `uv run ruff check src/` passes with no errors
- ✅ `uv run mypy src/monocli` passes type checking
- ✅ `uv run pytest` runs successfully (0 tests collected as expected)
- ✅ Package is importable: `uv run python -c "import monocli; print(monocli.__version__)"` returns 0.1.0

## Next Phase Readiness

Foundation tooling is complete and ready for:
- Phase 01-02: Pydantic models for MR/PR and Issue data structures
- Phase 01-03: Async subprocess utilities with Textual Workers API

All tooling is configured and tested. No blockers.

## Self-Check: PASSED

All files and commits verified present:
- pyproject.toml ✓
- src/monocli/__init__.py ✓
- src/monocli/py.typed ✓
- tests/__init__.py ✓
- tests/conftest.py ✓
- Commits: 1d50c55, c5b3052, 36f1afb, 063bf17 ✓

---
*Phase: 01-foundation*
*Completed: 2026-02-07*
