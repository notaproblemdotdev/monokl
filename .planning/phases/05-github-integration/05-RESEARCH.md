# Phase 5: GitHub Integration - Research

**Researched:** 2026-02-09
**Domain:** GitHub CLI (`gh`) adapter for PRs and Issues
**Confidence:** HIGH

## Summary

Researched the `gh` CLI (v2.83.2) to understand exact command syntax, JSON output formats, error handling patterns, and how to mirror the existing GitLabAdapter pattern. The project already has Pydantic models (`PullRequest`, `GitHubIssue`) in `models.py`, a `CLIAdapter` base class in `async_utils.py`, and established patterns in `GitLabAdapter` and `JiraAdapter` that should be closely followed.

The primary design decision is whether to use `gh pr list` (repo-scoped) vs `gh search prs` (cross-repo). The `gh pr list` command requires git remote context or `--repo` flag, while `gh search prs` works globally. **Recommendation: use `gh search prs` and `gh search issues`** for cross-repo coverage without requiring the user to be inside a GitHub repo, matching how the GitLab adapter uses `glab mr list --all --group` to search across a group.

**Primary recommendation:** Create `GitHubAdapter` inheriting from `CLIAdapter` using `gh search prs --author @me` and `gh search issues --assignee @me` with `--json` output, mapping fields to the existing Pydantic models. Use `gh auth status --active` for auth checking.

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `gh` CLI | 2.83.2+ | GitHub CLI for PRs/Issues | Official GitHub CLI, already planned |
| `CLIAdapter` base class | (internal) | Shared subprocess utilities | Already exists in `async_utils.py` |
| Pydantic `PullRequest` model | (internal) | PR data validation | Already exists in `models.py` |
| Pydantic `GitHubIssue` model | (internal) | Issue data validation | Already exists in `models.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `structlog` | (existing) | Structured logging | All adapter methods need logging |
| `CLIDetector` | (internal) | Startup detection | Register `gh` detector with `["auth", "status", "--active"]` |

### No New Dependencies Required

The phase requires zero new pip dependencies. Everything uses the existing `CLIAdapter` base class infrastructure.

## Architecture Patterns

### Recommended Project Structure (new files only)

```
src/monocli/adapters/
├── __init__.py          # Add GitHubAdapter export
├── github.py            # NEW: GitHubAdapter class
├── gitlab.py            # Existing (reference pattern)
├── jira.py              # Existing (reference pattern)
└── detection.py         # Existing (register gh detector)

tests/
├── test_github_adapter.py  # NEW: Tests mirroring test_gitlab_adapter.py
└── test_models.py          # MODIFY: May need label transformation tests
```

### Pattern 1: Adapter Class Structure (mirror GitLabAdapter exactly)

**What:** GitHubAdapter inherits from CLIAdapter, provides fetch methods and auth checking
**When to use:** Always — this is the established project pattern

```python
# Source: existing GitLabAdapter pattern
from monocli.async_utils import CLIAdapter
from monocli.exceptions import CLIAuthError, CLINotFoundError
from monocli.models import PullRequest, GitHubIssue

class GitHubAdapter(CLIAdapter):
    def __init__(self) -> None:
        super().__init__("gh")

    async def fetch_authored_prs(self, state: str = "open") -> list[PullRequest]:
        """Fetch PRs authored by current user across all repos."""
        args = [
            "search", "prs",
            "--author", "@me",
            "--state", state,
            "--json", "number,title,state,author,url,isDraft,createdAt,repository",
        ]
        raw_data = await self.fetch_json(args)
        return [PullRequest.model_validate(self._map_pr(item)) for item in raw_data]

    async def fetch_assigned_issues(self, state: str = "open") -> list[GitHubIssue]:
        """Fetch issues assigned to current user across all repos."""
        args = [
            "search", "issues",
            "--assignee", "@me",
            "--state", state,
            "--json", "number,title,state,author,url,labels,createdAt,assignees",
        ]
        raw_data = await self.fetch_json(args)
        return [GitHubIssue.model_validate(self._map_issue(item)) for item in raw_data]

    async def check_auth(self) -> bool:
        """Check if gh is authenticated."""
        try:
            await self.run(["auth", "status", "--active"], check=True, timeout=5.0)
            return True
        except (CLIAuthError, CLINotFoundError, TimeoutError):
            return False
```

### Pattern 2: Field Mapping (gh JSON → Pydantic model)

**What:** Transform `gh` CLI JSON fields to match existing Pydantic model field names
**When to use:** The `gh` CLI field names don't match the Pydantic models exactly

**Critical field mapping needed:**

For PRs (`gh search prs --json`):
```python
def _map_pr(self, data: dict) -> dict:
    """Map gh CLI PR fields to PullRequest model fields."""
    return {
        "number": data["number"],
        "title": data["title"],
        "state": data["state"],           # "open" from search (already lowercase)
        "author": data["author"],          # {"login": "user", ...} - compatible
        "html_url": data["url"],           # gh uses "url", model uses "html_url"
        "draft": data.get("isDraft", False),  # gh uses "isDraft", model uses "draft"
        "created_at": data.get("createdAt"),  # gh uses "createdAt", model uses "created_at"
    }
```

For Issues (`gh search issues --json`):
```python
def _map_issue(self, data: dict) -> dict:
    """Map gh CLI Issue fields to GitHubIssue model fields."""
    return {
        "number": data["number"],
        "title": data["title"],
        "state": data["state"],
        "author": data["author"],
        "html_url": data["url"],
        "labels": [label["name"] for label in data.get("labels", [])],  # Extract names!
        "created_at": data.get("createdAt"),
        "assignees": data.get("assignees", []),
    }
```

### Pattern 3: Auth Check Command

**What:** Use `gh auth status --active` instead of plain `gh auth status`
**Why critical:** Plain `gh auth status` exits with code 1 if ANY account (including inactive ones) has auth issues, even if the active account is fine. Using `--active` only checks the active account.

```python
# CORRECT: Only checks active account
await self.run(["auth", "status", "--active"], check=True, timeout=5.0)

# WRONG: Exits 1 if any account has issues (even inactive ones)
await self.run(["auth", "status"], check=True, timeout=5.0)
```

### Pattern 4: Detection Registration

**What:** Register `gh` detector in the DetectionRegistry alongside `glab` and `acli`
**Where:** In `MainScreen.detect_and_fetch()` method

```python
# In main_screen.py detect_and_fetch():
registry.register(CLIDetector("gh", ["auth", "status", "--active"]))
```

### Anti-Patterns to Avoid

- **Don't use `gh pr list` for the adapter:** Requires being inside a git repo with GitHub remotes. Use `gh search prs` instead for cross-repo coverage.
- **Don't pass JSON field names that don't exist:** `gh` will error if you request a field that doesn't exist for that command. The available fields differ between `pr list` and `search prs`.
- **Don't assume state case is consistent:** `gh pr list` returns UPPERCASE states (`"OPEN"`, `"MERGED"`, `"CLOSED"`), while `gh search prs` returns lowercase (`"open"`, `"closed"`). The existing `PullRequest` model validates `pattern=r"^(open|closed|merged)$"` which is lowercase only. Use `gh search prs` to get lowercase states matching the model.
- **Don't forget label transformation:** `gh` returns labels as objects `{"name": "bug", "color": "d73a4a", ...}` but the `GitHubIssue` model expects `list[str]`. Extract `.name` from each label.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subprocess management | Custom subprocess code | `CLIAdapter.run()` and `CLIAdapter.fetch_json()` | Already handles semaphores, timeouts, stdin blocking, cleanup |
| JSON parsing + validation | Manual dict access | `CLIAdapter.fetch_and_parse()` or `fetch_json()` + `model_validate()` | Pydantic validation catches bad data |
| Error classification | Custom stderr parsing | `raise_for_error()` in `exceptions.py` | Already detects auth patterns |
| CLI availability check | Custom `which` check | `CLIAdapter.is_available()` | Already cached, returns bool |
| Concurrent detection | Custom asyncio code | `DetectionRegistry.detect_all()` | Already handles concurrent detection with gather |

**Key insight:** The entire subprocess lifecycle is already handled by `CLIAdapter`. The adapter code should only be ~100 lines: init, fetch methods with field mapping, and auth check.

## Common Pitfalls

### Pitfall 1: State Case Mismatch Between `gh` Commands

**What goes wrong:** `gh pr list --json state` returns `"OPEN"`, `"CLOSED"`, `"MERGED"` (uppercase), but `gh search prs --json state` returns `"open"`, `"closed"` (lowercase). The existing `PullRequest` model validates lowercase only.
**Why it happens:** Different `gh` subcommands use different GraphQL queries with different response formatting.
**How to avoid:** Use `gh search prs` (lowercase) consistently, or normalize with `.lower()` if using `gh pr list`.
**Warning signs:** Pydantic `ValidationError` on `state` field with pattern mismatch.

### Pitfall 2: Label Format Mismatch

**What goes wrong:** The `GitHubIssue` model has `labels: list[str]` but `gh` returns `labels: [{"name": "bug", "id": "...", "color": "...", "description": "..."}]`.
**Why it happens:** `gh` returns full label objects from the API.
**How to avoid:** Transform labels in the mapping function: `[label["name"] for label in data.get("labels", [])]`
**Warning signs:** Pydantic validation error: "Input should be a valid string" when labels contain dicts.

### Pitfall 3: `gh auth status` Exit Code with Multiple Accounts

**What goes wrong:** `gh auth status` returns exit code 1 even when the active account is properly authenticated, if ANY other account has issues.
**Why it happens:** `gh` checks ALL accounts by default and reports failure if any are broken.
**How to avoid:** Always use `gh auth status --active` flag.
**Warning signs:** Auth check falsely returns `False` when user is actually logged in.

### Pitfall 4: Search API Rate Limits

**What goes wrong:** Search API has 30 requests/minute limit (vs 5000/hour for core API). Excessive polling could hit this.
**Why it happens:** GitHub's search API has stricter rate limits than REST/GraphQL.
**How to avoid:** Don't poll aggressively. The app fetches data once on startup, which is fine. If refresh is added later, respect the 30/min limit.
**Warning signs:** HTTP 403 or 422 errors from `gh` with rate limit messages.

### Pitfall 5: Missing `url` to `html_url` Mapping

**What goes wrong:** `gh` CLI JSON uses `url` for the web URL, but the `PullRequest` model field is `html_url`.
**Why it happens:** Different naming conventions between gh CLI and the model (which was designed to match GitHub API naming).
**How to avoid:** Always map `url` → `html_url` in the adapter's transform function.
**Warning signs:** Pydantic `ValidationError` for missing required field `html_url`.

### Pitfall 6: `isDraft` vs `draft` Field Name

**What goes wrong:** `gh` CLI uses `isDraft` in JSON output, but the `PullRequest` model uses `draft`.
**Why it happens:** `gh` CLI field names follow GraphQL naming conventions (camelCase).
**How to avoid:** Map `isDraft` → `draft` in the transform function.
**Warning signs:** The `draft` field defaults to `False` so this won't error — it will silently show all PRs as non-draft.

### Pitfall 7: `createdAt` vs `created_at` Field Name

**What goes wrong:** `gh` CLI uses `createdAt` (camelCase), model uses `created_at` (snake_case).
**Why it happens:** Same camelCase vs snake_case convention difference.
**How to avoid:** Map in transform function.
**Warning signs:** `created_at` defaults to `None`, so this fails silently — dates just won't display.

## Code Examples

### Example 1: Complete GitHubAdapter Class

```python
# Source: derived from existing GitLabAdapter + verified gh CLI output
"""GitHub CLI adapter for fetching pull requests and issues."""

from typing import Any

from monocli import get_logger
from monocli.async_utils import CLIAdapter
from monocli.exceptions import CLIAuthError, CLINotFoundError
from monocli.models import GitHubIssue, PullRequest

logger = get_logger(__name__)


class GitHubAdapter(CLIAdapter):
    """Adapter for GitHub CLI (gh) operations."""

    def __init__(self) -> None:
        super().__init__("gh")

    @staticmethod
    def _map_pr(data: dict[str, Any]) -> dict[str, Any]:
        """Map gh search prs JSON to PullRequest model fields."""
        return {
            "number": data["number"],
            "title": data["title"],
            "state": data["state"],
            "author": data["author"],
            "html_url": data["url"],
            "draft": data.get("isDraft", False),
            "created_at": data.get("createdAt"),
        }

    @staticmethod
    def _map_issue(data: dict[str, Any]) -> dict[str, Any]:
        """Map gh search issues JSON to GitHubIssue model fields."""
        return {
            "number": data["number"],
            "title": data["title"],
            "state": data["state"],
            "author": data["author"],
            "html_url": data["url"],
            "labels": [label["name"] for label in data.get("labels", [])],
            "created_at": data.get("createdAt"),
            "assignees": data.get("assignees", []),
        }

    async def fetch_authored_prs(self, state: str = "open") -> list[PullRequest]:
        """Fetch PRs authored by current user across all repos."""
        logger.info("Fetching GitHub PRs", state=state)
        args = [
            "search", "prs",
            "--author", "@me",
            "--state", state,
            "--json", "number,title,state,author,url,isDraft,createdAt",
        ]
        try:
            raw_data = await self.fetch_json(args)
            prs = [PullRequest.model_validate(self._map_pr(item)) for item in raw_data]
            logger.info("Fetched GitHub PRs", count=len(prs))
            return prs
        except CLIAuthError:
            logger.warning("Failed to fetch GitHub PRs - authentication error")
            raise
        except CLINotFoundError:
            logger.warning("Failed to fetch GitHub PRs - gh not found")
            raise

    async def fetch_assigned_issues(self, state: str = "open") -> list[GitHubIssue]:
        """Fetch issues assigned to current user across all repos."""
        logger.info("Fetching GitHub issues", state=state)
        args = [
            "search", "issues",
            "--assignee", "@me",
            "--state", state,
            "--json", "number,title,state,author,url,labels,createdAt,assignees",
        ]
        try:
            raw_data = await self.fetch_json(args)
            issues = [GitHubIssue.model_validate(self._map_issue(item)) for item in raw_data]
            logger.info("Fetched GitHub issues", count=len(issues))
            return issues
        except CLIAuthError:
            logger.warning("Failed to fetch GitHub issues - authentication error")
            raise
        except CLINotFoundError:
            logger.warning("Failed to fetch GitHub issues - gh not found")
            raise

    async def check_auth(self) -> bool:
        """Check if gh is authenticated (active account only)."""
        logger.debug("Checking GitHub authentication")
        try:
            await self.run(["auth", "status", "--active"], check=True, timeout=5.0)
            logger.debug("GitHub authenticated")
            return True
        except (CLIAuthError, CLINotFoundError, TimeoutError):
            logger.warning("GitHub not authenticated")
            return False
```

### Example 2: Detection Registration

```python
# In main_screen.py detect_and_fetch() method:
registry = DetectionRegistry()
registry.register(CLIDetector("glab", ["auth", "status"]))
registry.register(CLIDetector("gh", ["auth", "status", "--active"]))
registry.register(CLIDetector("acli", ["jira", "auth", "status"]))
```

### Example 3: Test Fixture - Sample PR Data (matching real gh output)

```python
# Source: actual gh search prs --json output, verified 2026-02-09
SAMPLE_PR_JSON = [
    {
        "author": {
            "id": "MDQ6VXNlcjQyOTQ0ODA=",
            "is_bot": False,
            "login": "testuser",
            "type": "User",
            "url": "https://github.com/testuser"
        },
        "createdAt": "2026-01-24T20:30:52Z",
        "isDraft": False,
        "number": 42,
        "state": "open",
        "title": "Add new feature",
        "url": "https://github.com/org/repo/pull/42"
    }
]
```

### Example 4: Test Fixture - Sample Issue Data (matching real gh output)

```python
# Source: actual gh search issues --json output, verified 2026-02-09
SAMPLE_ISSUE_JSON = [
    {
        "assignees": [
            {
                "id": "MDQ6VXNlcjQyOTQ0ODA=",
                "is_bot": False,
                "login": "testuser",
                "type": "User",
                "url": "https://github.com/testuser"
            }
        ],
        "author": {
            "id": "MDQ6VXNlcjMwNTAzNjk1",
            "is_bot": False,
            "login": "otheruser",
            "type": "User",
            "url": "https://github.com/otheruser"
        },
        "createdAt": "2026-01-20T10:00:00Z",
        "labels": [
            {
                "color": "d73a4a",
                "description": "Something isn't working",
                "id": "MDU6TGFiZWwxNTkzNDg0NjIw",
                "name": "bug"
            },
            {
                "color": "0dd8ac",
                "description": "New feature request",
                "id": "MDU6TGFiZWwxNjk4MDc2MTcz",
                "name": "enhancement"
            }
        ],
        "number": 99,
        "state": "open",
        "title": "Fix login flow",
        "url": "https://github.com/org/repo/issues/99"
    }
]
```

### Example 5: Test Pattern (matching existing test_gitlab_adapter.py structure)

```python
class TestGitHubAdapter:
    def test_adapter_init(self) -> None:
        adapter = GitHubAdapter()
        assert adapter.cli_name == "gh"
        assert adapter._available is None

    @pytest.mark.asyncio
    async def test_fetch_authored_prs_success(self) -> None:
        adapter = GitHubAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/gh"
            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(json.dumps(SAMPLE_PR_JSON).encode(), b"")
                )
                mock_exec.return_value = mock_proc

                prs = await adapter.fetch_authored_prs()

        assert len(prs) == 1
        assert prs[0].number == 42
        assert prs[0].title == "Add new feature"
        assert prs[0].state == "open"
        assert prs[0].author["login"] == "testuser"
        assert str(prs[0].html_url) == "https://github.com/org/repo/pull/42"
```

## gh CLI Command Reference

### Commands Used

| Command | Purpose | Exit Codes |
|---------|---------|------------|
| `gh search prs --author @me --state open --json fields` | Fetch user's PRs across all repos | 0=success, 1=error, 4=auth |
| `gh search issues --assignee @me --state open --json fields` | Fetch user's assigned issues across all repos | 0=success, 1=error, 4=auth |
| `gh auth status --active` | Check authentication for active account | 0=authed, 1=not authed |

### JSON Field Name Mapping

**PR fields (`gh search prs --json`):**

| gh CLI Field | Pydantic Model Field | Transform Needed |
|-------------|---------------------|-----------------|
| `number` | `number` | None |
| `title` | `title` | None |
| `state` | `state` | None (lowercase from search) |
| `author` | `author` | None (dict with `login` key) |
| `url` | `html_url` | **Rename** |
| `isDraft` | `draft` | **Rename** |
| `createdAt` | `created_at` | **Rename** |

**Issue fields (`gh search issues --json`):**

| gh CLI Field | Pydantic Model Field | Transform Needed |
|-------------|---------------------|-----------------|
| `number` | `number` | None |
| `title` | `title` | None |
| `state` | `state` | None |
| `author` | `author` | None |
| `url` | `html_url` | **Rename** |
| `labels` | `labels` | **Extract `.name` from each object** |
| `createdAt` | `created_at` | **Rename** |
| `assignees` | `assignees` | None (list of dicts) |

### gh Exit Codes

| Code | Meaning | Maps To |
|------|---------|---------|
| 0 | Success | Normal result |
| 1 | Error (generic) | `CLIError` |
| 2 | Cancelled | `CLIError` |
| 4 | Authentication required | `CLIAuthError` |

**Important for `raise_for_error()`:** The existing `CLIAuthError.AUTH_PATTERNS` checks stderr for patterns like "not authenticated", "unauthorized", "401". For `gh`, exit code 4 is the definitive auth error signal. The stderr text from `gh` on auth failure typically contains "not logged in" which matches the existing patterns. This should work without modification, but test to confirm.

### `gh search prs` vs `gh pr list` Decision

| Feature | `gh pr list` | `gh search prs` |
|---------|-------------|-----------------|
| Repo required | Yes (git remote or `--repo`) | No (global search) |
| State case | UPPERCASE (`"OPEN"`) | lowercase (`"open"`) |
| `@me` filter | `--author @me` | `--author @me` |
| JSON fields | 48 fields available | 18 fields available |
| Rate limit | Core API (5000/hr) | Search API (30/min) |
| Default limit | 30 | 30 |

**Decision: Use `gh search prs`** because:
1. Works without repo context — monocli is a dashboard, not repo-specific
2. Returns lowercase state matching the Pydantic model pattern validation
3. The 18 available fields include everything we need
4. Rate limit of 30/min is fine for dashboard startup (1-2 calls total)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `gh auth status` (all accounts) | `gh auth status --active` | gh 2.40+ | Correctly checks only active account |
| `gh pr list` (repo-scoped) | `gh search prs` (global) | gh 2.5+ | Cross-repo search without `--repo` |

## Open Questions

1. **Config for GitHub repos/orgs**
   - What we know: GitLab adapter requires `MONOCLI_GITLAB_GROUP` config. `gh search prs` works globally without config.
   - What's unclear: Should we add optional `MONOCLI_GITHUB_ORG` or `MONOCLI_GITHUB_REPOS` filtering? The `--owner` flag on `gh search prs` could filter by org.
   - Recommendation: Start without config (global search), add optional org filtering as enhancement later. Keep it simple for Phase 5.

2. **Search result limit**
   - What we know: `gh search prs` defaults to 30 results. `--limit` can increase up to 1000.
   - What's unclear: Is 30 sufficient for a dashboard view?
   - Recommendation: Use default 30 for now. It matches what `gh pr list` defaults to and is reasonable for a dashboard.

3. **PR `merged` state in search**
   - What we know: `gh search prs` `--state` only accepts `open` and `closed`. Merged PRs are a subset of closed. The `PullRequest` model allows `"merged"` state, but `gh search prs` returns `"closed"` for merged PRs (no separate `"merged"` state).
   - What's unclear: Whether we need merged state distinction.
   - Recommendation: For the initial implementation, just fetch `--state open`. Dashboard shows active work. The state values from search will be `"open"` or `"closed"`, never `"merged"`. The `PullRequest` model already accepts all three, so no model change needed.

## Sources

### Primary (HIGH confidence)
- **`gh` CLI v2.83.2 help output** — `gh pr list --help`, `gh issue list --help`, `gh auth status --help`, `gh search prs --help`, `gh search issues --help`, `gh help exit-codes` — all verified locally
- **Live `gh` CLI JSON output** — Ran actual commands against real GitHub repos to capture exact JSON field names, structure, and casing
- **Existing codebase** — `src/monocli/adapters/gitlab.py`, `src/monocli/async_utils.py`, `src/monocli/models.py`, `src/monocli/exceptions.py`, `src/monocli/adapters/detection.py`

### Secondary (MEDIUM confidence)
- **GitHub API rate limits** — Verified via `gh api rate_limit` (search: 30/min, core: 5000/hr)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries/tools already exist in codebase
- Architecture: HIGH — mirroring existing GitLabAdapter pattern exactly
- Field mappings: HIGH — verified with live `gh` CLI JSON output
- Pitfalls: HIGH — discovered through real testing (state case, label objects, auth exit codes)
- Auth patterns: HIGH — tested `gh auth status --active` vs `gh auth status` with multi-account setup

**Research date:** 2026-02-09
**Valid until:** 2026-04-09 (stable — gh CLI is mature, field names don't change between minor versions)
