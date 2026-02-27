# Monokl Plan (Living Document)

This file captures agreed product/CLI decisions so they remain discoverable outside chat history.

## Vision
Monokl is a "daily developer cockpit" with multiple surfaces sharing the same core entities:
- Dashboard: work items, code reviews, pipelines.
- CLI workflows: repeatable commands that automate day-to-day actions.
- Agent: optional, explicit LLM-backed assistance (future).

## Key Decisions (So Far)
- Running `monokl` with no args shows help (help-first).
- CLI is organized task-first (work/review/pipeline/...).
- Dashboard entrypoint is `monokl dash` (not `monokl tui`).
- Web-serving the dashboard is `monokl dash --web` (not `monokl web`).
- No backwards-compatible aliases for renamed commands.

## CLI: Dashboard
- `monokl dash [--debug] [--offline] [--db-path ...] [--clear-cache]`
- `monokl dash --web [--host localhost] [--port 6969] [--no-open] [--debug] [--offline] [--db-path ...]`

Behavior:
1. Configure logging.
2. Apply env vars (`MONOKL_OFFLINE_MODE`, `MONOKL_DB_PATH`) the same way for TUI and `--web`.
3. Validate keyring availability.
4. If `--web` is set, start `textual-serve` running `python -m monokl dash` with matching flags.
5. Otherwise run the Textual TUI directly.

## CLI: Workflows (Planned)
This is the intended command taxonomy; implement incrementally.

### Work items
- `monokl work list`
- `monokl work show <id>`
- `monokl work open <id>`
- `monokl work start <id>`

Defaults for `work start`:
- Worktrees under repo-local `.worktrees/`.
- Branch name: `feature/<ID>-<slug>`.

### Code reviews
- `monokl review list`
- `monokl review show <id>`
- `monokl review open <id>`
- `monokl review checkout <id>`

### Pipelines
- `monokl pipeline list`
- `monokl pipeline open <pipeline_id|review_id>`
- `monokl pipeline watch <pipeline_id|review_id>`
- `monokl pipeline retry <pipeline_id>`

## CLI: Agent (Future)
Use `monokl agent ...` (no implicit AI; always explicit).
- `monokl agent chat`
- `monokl agent summarize ...`
- `monokl agent standup ...`
