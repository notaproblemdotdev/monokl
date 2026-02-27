"""Deterministic model and exception factories for tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC
from datetime import datetime

from monokl.exceptions import CLIAuthError
from monokl.exceptions import CLIError
from monokl.models import CodeReview
from monokl.models import JiraPieceOfWork
from monokl.models import TodoistPieceOfWork


def make_code_review(
    *,
    idx: int,
    adapter_type: str = "gitlab",
    adapter_icon: str = "🦊",
    state: str = "open",
    title: str | None = None,
    author: str = "test-user",
    created_at_factory: Callable[[], datetime] | None = None,
) -> CodeReview:
    """Create a deterministic CodeReview model for tests."""
    created_at = (
        created_at_factory()
        if created_at_factory is not None
        else datetime(2025, 1, 1, 12, 0, idx, tzinfo=UTC)
    )
    key_prefix = "!" if adapter_type in {"gitlab", "bitbucket"} else "#"
    return CodeReview(
        id=f"{adapter_type}-{idx}",
        key=f"{key_prefix}{idx}",
        title=title or f"{adapter_type} review {idx}",
        state=state,
        author=author,
        source_branch=f"feature/{adapter_type}-{idx}",
        url=f"https://example.test/{adapter_type}/reviews/{idx}",
        created_at=created_at,
        draft=False,
        adapter_type=adapter_type,
        adapter_icon=adapter_icon,
    )


def make_jira_item(
    *,
    idx: int,
    status: str = "In Progress",
    priority: str = "High",
    summary: str | None = None,
) -> JiraPieceOfWork:
    """Create a deterministic Jira work item for tests."""
    return JiraPieceOfWork(
        key=f"PROJ-{100 + idx}",
        fields={
            "summary": summary or f"Jira work item {idx}",
            "status": {"name": status},
            "priority": {"name": priority},
            "assignee": {"displayName": "Test User"},
        },
        self=f"https://jira.example.test/rest/api/2/issue/{10_000 + idx}",
    )


def make_todoist_item(
    *,
    idx: int,
    priority: int = 2,
    content: str | None = None,
    completed: bool = False,
) -> TodoistPieceOfWork:
    """Create a deterministic Todoist work item for tests."""
    return TodoistPieceOfWork(
        id=str(100_000 + idx),
        content=content or f"Todoist task {idx}",
        priority=priority,
        due=None,
        project_id="proj-1",
        project_name="Work",
        url=f"https://todoist.example.test/tasks/{100_000 + idx}",
        is_completed=completed,
    )


def make_cli_auth_error(
    *,
    command: list[str] | None = None,
    stderr: str = "Not authenticated",
    returncode: int = 1,
) -> CLIAuthError:
    """Create a valid CLIAuthError for test scenarios."""
    return CLIAuthError(command or ["glab", "auth", "status"], returncode, stderr)


def make_cli_error(
    *,
    command: list[str] | None = None,
    stderr: str = "CLI command failed",
    returncode: int = 1,
) -> CLIError:
    """Create a valid CLIError for test scenarios."""
    return CLIError(command or ["cli", "command"], returncode, stderr)
