# Mono CLI

## What This Is

A unified terminal user interface (TUI) that aggregates work items and pull/merge requests from multiple developer platforms into a single dashboard. Built with the Textual framework, it calls existing CLI tools (gh, glab, acli) that are already authenticated, providing a cohesive view of what the user needs to work on across Jira, GitHub, and GitLab.

## Core Value

One dashboard showing all assigned work items and pending PRs/MRs without switching between browser tabs or context switching between platforms.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] TUI framework using Textual renders two-section dashboard
- [ ] Auto-detect which CLIs are installed (gh, glab, acli) and show only corresponding sections
- [ ] Dashboard displays all sections from start with per-section loading spinners
- [ ] Async data fetching without blocking UI
- [ ] PRs/MRs section: merge/pull requests assigned to user OR created by user
- [ ] Work Items section: issues assigned to user that are not closed (GitHub issues + Jira work items)
- [ ] Display format for each item: Key + Title + Status + Priority
- [ ] Press 'o' key to open selected item in default browser
- [ ] Auto-refresh capability for keeping data current
- [ ] Manual refresh capability (r/F5) for forcing updates
- [ ] Background reload without blocking UI interactions

### Out of Scope

- **Real-time notifications** — Out of v1 scope; focus on on-demand dashboard view
- **Modifying items from CLI** — View-only in v1, editing via web interface
- **Custom theming** — Standard Textual themes sufficient for MVP
- **Offline mode** — Requires active internet connection to fetch data
- **Caching strategies** — Fresh fetch on load, caching may be added in v2
- **Non-terminal interfaces** — TUI-only, no web or desktop versions

## Context

**Target Users:** Developers working with Jira, GitHub, and/or GitLab who prefer terminal interfaces over browser-based UIs and want a unified view of their work.

**Problem Being Solved:** Context switching between multiple browser tabs (Jira for issues, GitHub/GitLab for PRs) to see what's on the user's plate. This tool provides a single command (`monocli`) that aggregates everything in one view.

**Data Sources:**
- **GitHub:** `gh` CLI for pull requests
- **GitLab:** `glab` CLI for merge requests  
- **Jira:** `acli` CLI for work items

**Authentication:** Relies on existing CLI authentication; no separate auth mechanism needed.

**Architecture Approach:**
- Plugin-style architecture for different data sources (CLI adapters)
- Each source has its own async loader
- Loading states per section with spinners
- Non-blocking UI throughout

## Constraints

- **Tech stack:** Python with Textual framework for TUI
- **Dependencies:** Requires `gh`, `glab`, and/or `acli` CLIs to be installed and authenticated
- **Async requirement:** Must load data asynchronously without blocking UI
- **UI responsiveness:** Background reloads must not freeze or interrupt user interaction
- **Layout:** Two main sections — PRs/MRs and Work Items

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Textual framework | Modern Python TUI library with async support | — Pending |
| Shell out to existing CLIs vs APIs | Reuse existing auth, simpler implementation, no credential management | — Pending |
| Per-section loading spinners | Users see dashboard immediately, async feedback per data source | — Pending |
| 'o' key for opening browser | Vim-style convention familiar to CLI users | — Pending |
| Two-section layout (PRs + Work Items) | Logical grouping by task type vs source | — Pending |
| Auto-detect CLIs vs explicit config | Better UX — only show relevant sections, no config needed | — Pending |

---
*Last updated: 2025-02-07 after initialization*
