# Testing Quality Inventory

## Contract Matrix

| Area | Current API | Drift Previously Seen | Resolution |
|---|---|---|---|
| Main screen sections | `screen.code_review_section`, `screen.piece_of_work_section` | tests used `screen.mr_container`, `screen.work_section` | tests migrated to current names |
| Code review section | `CodeReviewSection` with `assigned_to_me_section` and `opened_by_me_section` | constructor referenced `opened_by_me_section` before init | constructor init order fixed |
| WorkStore cached deserialization | `CodeReview.model_validate(...)` in `_deserialize_code_reviews` | runtime `NameError` due missing import | runtime import of `CodeReview` added |
| Auth exceptions | `CLIAuthError(command, returncode, stderr)` | tests instantiated with single string | shared factory creates valid exception objects |

## Failure Inventory and Priorities

| Priority | File(s) | Class | Root Cause |
|---|---|---|---|
| P0 | `src/monokl/ui/sections.py` | app regression | `CodeReviewSection` child not initialized before access |
| P0 | `src/monokl/db/work_store.py` | app regression | cached review deserialization missing runtime symbol |
| P1 | `tests/ui/test_main_screen.py`, `tests/ui/test_navigation.py` | test drift | legacy screen/section names and assumptions |
| P1 | `tests/integration/*` | test drift + harness quality | mixed ad-hoc mocks, duplicate source identities, invalid exception constructors |
| P2 | `tests/integration/*` | teardown hygiene | inconsistent DB teardown and loop-close warnings |

## Implemented Direction

- Shared deterministic stubs and factories in `tests/support/`.
- Integration markers split into `integration_smoke` and `integration_full`.
- Integration and UI tests realigned to current APIs and stub-backed data flow.
