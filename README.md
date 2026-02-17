# Monocli

<p align="center">
  <img src=".assets/logo.png" alt="Monocli Logo" width="200">
</p>

A unified terminal dashboard for managing pull/merge requests from GitLab and work items from Jira. Built with an extensible architecture to support additional platforms.

## Features

- **GitLab Integration**: View merge requests assigned to you and opened by you
- **Jira Integration**: View work items assigned to you
- **Unified Dashboard**: Single interface for all your development tasks
- **Keyboard Navigation**: Tab to switch sections, j/k to navigate, o to open in browser

## Installation

```bash
pip install monocli
```

Or with uv:

```bash
uv pip install monocli
```

## Usage

Run the dashboard:

```bash
monocli
```

Or:

```bash
python -m monocli
```

Or with uvx:

```bash
uvx monocli
# or
uvx https://github.com/notaproblemdotdev/monocli
```

## Configuration

The app requires the following CLIs to be installed and authenticated:

- `glab` - GitLab CLI
- `acli` - Atlassian CLI (for Jira)

Configure your GitLab group and Jira settings in `~/.config/monocli/config.yaml`:

```yaml
gitlab:
  group: your-group-name

jira:
  base_url: https://your-company.atlassian.net
```

Alternatively, use environment variables:

```bash
export MONOCLI_GITLAB_GROUP="your-group-name"
export MONOCLI_JIRA_BASE_URL="https://your-company.atlassian.net"
```

## Development

```bash
# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest

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
