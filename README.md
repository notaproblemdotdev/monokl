# Monocle

<p align="center">
  <img src=".assets/logo.png" alt="Monocle Logo" width="200">
</p>

A unified terminal dashboard for managing pull/merge requests from GitLab and work items from Jira. Built with an extensible architecture to support additional platforms.

## Features

- **GitLab Integration**: View merge requests assigned to you and opened by you
- **Jira Integration**: View work items assigned to you
- **Unified Dashboard**: Single interface for all your development tasks
- **Keyboard Navigation**: Tab to switch sections, j/k to navigate, o to open in browser

## Installation

```bash
pip install monocle
```

Or with uv:

```bash
uv pip install monocle
```

## Usage

Run the dashboard:

```bash
monocle
```

Or:

```bash
python -m monocle
```

Or with uvx:

```bash
uvx monocle
# or
uvx https://github.com/notaproblemdotdev/monocle
```

## Configuration

The app requires the following CLIs to be installed and authenticated:

- `glab` - GitLab CLI
- `acli` - Atlassian CLI (for Jira)

Configure your GitLab group and Jira settings in `~/.config/monocle/config.yaml`:

```yaml
gitlab:
  group: your-group-name

jira:
  base_url: https://your-company.atlassian.net
```

Alternatively, use environment variables:

```bash
export MONOCLE_GITLAB_GROUP="your-group-name"
export MONOCLE_JIRA_BASE_URL="https://your-company.atlassian.net"
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
