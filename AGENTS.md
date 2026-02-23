# Agents

## Development Environment

This project uses **uv** for all development tasks. Never use `python`, `pip`, or `pytest` directly — always prefix with `uv run`.

```bash
# Run the app
uv run python -m monocle

# Run with hot reload (for UI development)
uv run monocle-dev

# Run tests
uv run python -m pytest
uv run python -m pytest tests/ui/test_sections.py -v   # specific test file

# Linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking
uv run ty src/

# Install dependencies (including dev)
uv sync --extra dev
```

## Project Structure

- `src/monocle/` — main package (src layout)
- `src/monocle/models.py` — Pydantic models (MergeRequest, JiraWorkItem)
- `src/monocle/async_utils.py` — CLIAdapter base class, async subprocess utilities
- `src/monocle/exceptions.py` — CLIAuthError, CLINotFoundError, CLIError
- `src/monocle/adapters/` — CLI adapters (GitLab, Jira) and detection
- `src/monocle/ui/` — Textual UI (sections, main screen, app)
- `tests/` — pytest test suite

## Code Quality

- **Ruff** for linting and formatting (rules: E, F, I, N, W, UP, B, C4, SIM)
- **ty** (Astral's type checker) with strict mode enabled
- **pytest** with pytest-asyncio (asyncio_mode = "auto") and coverage
- Python 3.13+

## Coding Principles

- **No unnecessary shortcuts** — Avoid quick fixes or hacky solutions that create technical debt. Take the time to implement proper solutions.
- **Prefer abstractions and generics** — Use important abstractions and generic functions when possible. Extract common patterns into reusable components.
- **KISS** — Keep It Simple, Stupid. The simplest solution is often the best. Avoid over-engineering.
- **DRY** — Don't Repeat Yourself. Extract duplicated code into shared utilities, functions, or classes.
- **YAGNI** — You Aren't Gonna Need It. Don't implement features until you actually need them. Avoid speculative coding.
- **SOLID** — Follow SOLID principles:
  - **S**ingle Responsibility Principle
  - **O**pen/Closed Principle
  - **L**iskov Substitution Principle
  - **I**nterface Segregation Principle
  - **D**ependency Inversion Principle
