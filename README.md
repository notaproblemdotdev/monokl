# Monokl

<p align="center">
  <img src=".assets/logo.png" alt="Monokl Logo" width="200">
</p>

A collection of developer tools and a unified terminal dashboard for managing pull/merge requests from GitLab and work items from Jira.

## Why "Monokl"?

The name evolved through a few iterations:

1. **monocli** — one CLI for a lot of things, an easy entrypoint for the user
2. **monocle** — one good looking monocle to see stuff easily, so the dev's life will be easier
3. **monokl** — "monocle" in Polish (the author is Polish)

The goal: make a developer's daily life easier with a unified terminal dashboard and useful tools.

## Installation

```bash
pip install monokl
```

Or with uv:

```bash
uv pip install monokl
```

## Tools

Monokl provides a collection of useful developer tools under the `tool` command.

### UUID Generator

Generate UUID4 strings:

```bash
# Generate a single UUID
monokl tool uuid

# Generate multiple UUIDs
monokl tool uuid --count 5

# Output as JSON
monokl tool uuid --format json

# Uppercase output
monokl tool uuid --uppercase

# Without hyphens
monokl tool uuid --no-hyphens
```

### Network Tools

Test network connectivity and track response times:

```bash
# Ping a URL
monokl tool network ping https://example.com

# Store result in database
monokl tool network ping https://example.com --store

# Output as JSON
monokl tool network ping https://example.com --json

# Custom timeout (default 10s)
monokl tool network ping https://example.com --timeout 5

# View ping history with ASCII chart
monokl tool network report

# Filter by URL
monokl tool network report --url https://example.com

# Show last N results
monokl tool network report --last 50

# Clear ping history
monokl tool network clear
monokl tool network clear --url https://example.com  # clear specific URL only
```

## Dashboard (Experimental)

> **Note**: The dashboard feature is currently experimental and under active development.

A unified TUI dashboard for viewing merge requests and work items:

```bash
# Launch the TUI dashboard
monokl dash

# Serve in browser (via textual-serve)
monokl dash --web

# Custom port/host for web mode
monokl dash --web --port 8080 --host 0.0.0.0

# Offline mode (cached data only)
monokl dash --offline

# Clear cache
monokl dash --clear-cache
```

### Dashboard Configuration

The dashboard requires the following CLIs to be installed and authenticated:

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

## Other Commands

```bash
# View logs
monokl logs

# Interactive setup
monokl setup

# Show version
monokl --version
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

## License

MIT
