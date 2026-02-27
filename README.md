# Monokl

<p align="center">
  <img src=".assets/logo.png" alt="Monokl Logo" width="200">
</p>

A unified terminal dashboard for managing pull/merge requests from GitLab and work items from Jira. Built with an extensible architecture to support additional platforms.

## Why "Monokl"?

The name evolved through a few iterations:

1. **monocli** — one CLI for a lot of things, an easy entrypoint for the user
2. **monocle** — one good looking monocle to see stuff easily, so the dev's life will be easier
3. **monokl** — "monocle" in Polish (the author is Polish)

The goal: make a developer's daily life easier with a unified terminal dashboard.

## Features

- **GitLab Integration**: View merge requests assigned to you and opened by you
- **Jira Integration**: View work items assigned to you
- **Unified Dashboard**: Single interface for all your development tasks
- **Keyboard Navigation**: Tab to switch sections, j/k to navigate, o to open in browser

## Installation

```bash
pip install monokl
```

Or with uv:

```bash
uv pip install monokl
```

## Usage

Run the dashboard:

```bash
monokl dash
```

Run the dashboard in the browser:

```bash
monokl dash --web
```

Or:

```bash
python -m monokl dash
```

Or with uvx:

```bash
uvx monokl dash
# or
uvx https://github.com/notaproblemdotdev/monokl dash
```

## Configuration

The app requires the following CLIs to be installed and authenticated:

- `glab` - GitLab CLI
- `acli` - Atlassian CLI (for Jira)

Configure your GitLab group and Jira settings in `~/.config/monokl/config.yaml`:

```yaml
gitlab:
  group: your-group-name

jira:
  base_url: https://your-company.atlassian.net
```

Alternatively, use environment variables:

```bash
export MONOKL_GITLAB_GROUP="your-group-name"
export MONOKL_JIRA_BASE_URL="https://your-company.atlassian.net"
```

## Development

```bash
# Install dependencies
uv sync --extra dev

# Run tests
uv run python -m pytest
uv run python -m pytest -m integration_smoke
uv run python -m pytest -m integration_full
uv run python -m pytest -m "integration and not snapshot"

# Run linting
uv run ruff check .

# Run type checking
uv run ty src/
```

## Future Plans

Support for additional platforms is being considered:

- **GitHub** - Pull Requests and Issues
- **Bitbucket** - Pull Requests
- **Trello** - Cards and Boards
- **Todoist** - Tasks and Projects

## License

MIT
