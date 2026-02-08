---
phase: 04-add-logging
plan: 01
subsystem: logging
requires: []
provides:
  - Structured logging with structlog
  - Console and file output
  - Configurable log levels
  - Sensitive data filtering
affects:
  - Future debugging and monitoring features
  - CLI adapter logging
tech-stack:
  added: [structlog>=24.1.0]
  patterns: [Structured logging, Processor chain pattern]
key-files:
  created:
    - src/monocli/logging_config.py
    - tests/test_logging.py
  modified:
    - pyproject.toml
    - src/monocli/__init__.py
    - src/monocli/__main__.py
    - src/monocli/adapters/gitlab.py
    - src/monocli/adapters/jira.py
    - src/monocli/adapters/detection.py
decisions:
  - Use structlog for structured JSON logging with processor chain
  - Console output: human-readable format (ConsoleRenderer)
  - File output: JSON format for production/analysis
  - Log directory: ~/.local/share/monocli/logs/monocli_YYYY-MM-DD.log
  - Support LOG_LEVEL env variable (DEBUG, INFO, WARNING, ERROR)
  - Add --debug CLI flag for verbose logging
  - Implement sensitive data filtering processor for security
metrics:
  duration: "8m"
  completed: "2026-02-08"
---

# Phase 4 Plan 1: Add Logging with Structlog Summary

**Objective:** Set up structlog for structured logging with console and file output, configurable log levels, and debug mode support.

## What Was Built

A complete structured logging infrastructure using structlog:

1. **Logging Configuration Module** (`logging_config.py`)
   - `configure_logging(debug: bool)` - Configures structlog with processors
   - `get_logger(name)` - Returns a BoundLogger for modules
   - `ensure_log_dir()` - Creates log directory if needed
   - `get_log_file_path()` - Returns dated log file path
   - `filter_sensitive_data()` - Processor to mask tokens/passwords

2. **Console Output**
   - Human-readable format with colors (ConsoleRenderer)
   - Shows timestamp, log level, message, and structured data

3. **File Output**
   - JSON format for production/analysis
   - Log rotation by date: `monocli_YYYY-MM-DD.log`
   - Location: `~/.local/share/monocli/logs/`

4. **CLI Integration**
   - `--debug` flag enables DEBUG level logging
   - `--version` flag shows version
   - Logging configured before app starts
   - Startup message logged with version info

5. **Adapter Logging**
   - GitLabAdapter: Logs fetch operations, auth checks, errors
   - JiraAdapter: Logs fetch operations, auth checks, errors
   - DetectionRegistry: Logs CLI detection results

6. **Security Features**
   - Sensitive data filtering processor
   - Masks: token, password, secret, api_key, auth, credential, etc.
   - Case-insensitive pattern matching

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Use structlog | Industry standard for structured logging in Python |
| Processor chain | Clean separation of concerns (timestamp, level, filtering) |
| File + Console | Console for dev visibility, file for analysis |
| Date-based files | Simple rotation without complexity |
| Env var + CLI flag | Flexible log level configuration |
| Lazy proxy loggers | structlog's standard behavior for performance |

## API Usage

```python
from monocli import get_logger

logger = get_logger(__name__)
logger.info("User action", user_id=123, action="login")
logger.debug("Processing data", item_count=42)
logger.error("Operation failed", error_code=500)
```

## CLI Usage

```bash
# Run with default INFO level
uv run monocli

# Run with DEBUG logging
uv run monocli --debug

# Set log level via environment
LOG_LEVEL=WARNING uv run monocli
```

## Testing

Created comprehensive tests (`tests/test_logging.py`):
- 16 tests covering all functionality
- Log directory creation
- Log level configuration
- Sensitive data filtering
- File output verification

All tests pass:
```bash
uv run pytest tests/test_logging.py -v
# 16 passed
```

## Files Changed

```
pyproject.toml                           +1 line (structlog dependency)
src/monocli/__init__.py                  +4 lines (export logging functions)
src/monocli/__main__.py                  +21 lines (argparse, logging setup)
src/monocli/logging_config.py            192 lines (new module)
src/monocli/adapters/gitlab.py           +15 lines (logging calls)
src/monocli/adapters/jira.py             +15 lines (logging calls)
src/monocli/adapters/detection.py        +11 lines (logging calls)
tests/test_logging.py                    236 lines (new test module)
```

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Verification

| Criteria | Status |
|----------|--------|
| structlog dependency added | ✓ pyproject.toml updated |
| logging_config.py module | ✓ Created with all functions |
| Logs to file | ✓ ~/.local/share/monocli/logs/monocli_YYYY-MM-DD.log |
| Console output | ✓ Human-readable with colors |
| --debug flag | ✓ Supported and functional |
| LOG_LEVEL env var | ✓ Respected in configure_logging() |
| Sensitive data filtering | ✓ Masks tokens, passwords, etc. |
| Adapter logging | ✓ All adapters use get_logger() |
| Tests pass | ✓ 16/16 tests passing |

## Next Steps

Phase 4 complete! The logging infrastructure is ready for:
- Adding more detailed logging throughout the codebase
- Log analysis and monitoring
- Production debugging with structured logs

## Commit

`ba119b8` feat(04-01): Add structured logging with structlog

## Self-Check: PASSED

- [x] src/monocli/logging_config.py exists
- [x] tests/test_logging.py exists
- [x] Commit ba119b8 exists
- [x] Commit 404ed12 exists
