"""Pydantic models for platform data structures.

This module provides validated data models for parsing CLI outputs from
gh (GitHub), glab (GitLab), and acli (Jira).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, HttpUrl
from typing_extensions import Annotated


def parse_datetime(value: datetime | str | None) -> datetime | None:
    """Parse ISO 8601 datetime string or return datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Try parsing ISO 8601 format (handles both 'Z' and '+00:00' suffixes)
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    raise ValueError(f"Invalid datetime value: {value}")


# Type alias for datetime fields that accept ISO 8601 strings
IsoDateTime = Annotated[datetime | None, BeforeValidator(parse_datetime)]


class WorkItemStatus(str, Enum):
    """Work item status enumeration."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class Priority(str, Enum):
    """Priority level enumeration."""

    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"


class PullRequest(BaseModel):
    """GitHub Pull Request model.

    Validates GitHub PR data from gh CLI --json output.

    Attributes:
        number: PR number
        title: PR title
        state: PR state ("open", "closed", "merged")
        author: Dict containing author information with 'login' key
        html_url: PR URL
        draft: Whether the PR is a draft
        created_at: When the PR was created (ISO 8601 format)
        body: Optional PR description
    """

    model_config = ConfigDict(strict=True, validate_assignment=True)

    number: int = Field(..., description="Pull request number", ge=1)
    title: str = Field(..., description="Pull request title", min_length=1)
    state: str = Field(
        ...,
        description="Pull request state",
        pattern=r"^(open|closed|merged)$",
    )
    author: dict[str, Any] = Field(
        ...,
        description="Author information with 'login' key",
    )
    html_url: HttpUrl = Field(..., description="Pull request URL")
    draft: bool = Field(default=False, description="Whether this is a draft PR")
    created_at: IsoDateTime = Field(
        default=None,
        description="When the PR was created (ISO 8601 format)",
    )
    body: str | None = Field(default=None, description="Pull request description")

    def display_key(self) -> str:
        """Return formatted key for display."""
        return f"#{self.number}"

    def display_status(self) -> str:
        """Return normalized status string."""
        return self.state.upper()

    def is_open(self) -> bool:
        """Check if PR is open/ongoing."""
        return self.state == "open"


class MergeRequest(BaseModel):
    """GitLab Merge Request model.

    Validates GitLab MR data from glab CLI --json output.

    Attributes:
        iid: MR number (internal ID)
        title: MR title
        state: MR state ("opened", "closed", "merged", "locked")
        author: Dict containing author information with 'name' and 'username' keys
        web_url: MR URL
        source_branch: Source branch name
        target_branch: Target branch name
        created_at: When the MR was created (ISO 8601 format)
        draft: Whether the MR is a draft
        description: Optional MR description
    """

    model_config = ConfigDict(strict=True, validate_assignment=True)

    iid: int = Field(..., description="Merge request internal ID", ge=1)
    title: str = Field(..., description="Merge request title", min_length=1)
    state: str = Field(
        ...,
        description="Merge request state",
        pattern=r"^(opened|closed|merged|locked)$",
    )
    author: dict[str, Any] = Field(
        ...,
        description="Author information with 'name' and 'username' keys",
    )
    web_url: HttpUrl = Field(..., description="Merge request URL")
    source_branch: str = Field(..., description="Source branch name")
    target_branch: str = Field(..., description="Target branch name")
    created_at: IsoDateTime = Field(
        default=None,
        description="When the MR was created (ISO 8601 format)",
    )
    draft: bool = Field(default=False, description="Whether this is a draft MR")
    description: str | None = Field(default=None, description="Merge request description")

    def display_key(self) -> str:
        """Return formatted key for display."""
        return f"!{self.iid}"

    def display_status(self) -> str:
        """Return normalized status string."""
        return self.state.upper()

    def is_open(self) -> bool:
        """Check if MR is open/ongoing."""
        return self.state == "opened"


class GitHubIssue(BaseModel):
    """GitHub Issue model.

    Validates GitHub Issue data from gh CLI --json output.

    Attributes:
        number: Issue number
        title: Issue title
        state: Issue state ("open", "closed")
        author: Dict containing author information with 'login' key
        html_url: Issue URL
        labels: List of label names
        created_at: When the issue was created (ISO 8601 format)
        body: Optional issue description
        assignees: List of assignee information
    """

    model_config = ConfigDict(strict=True, validate_assignment=True)

    number: int = Field(..., description="Issue number", ge=1)
    title: str = Field(..., description="Issue title", min_length=1)
    state: str = Field(
        ...,
        description="Issue state",
        pattern=r"^(open|closed)$",
    )
    author: dict[str, Any] = Field(
        ...,
        description="Author information with 'login' key",
    )
    html_url: HttpUrl = Field(..., description="Issue URL")
    labels: list[str] = Field(
        default_factory=list,
        description="List of label names",
    )
    created_at: IsoDateTime = Field(
        default=None,
        description="When the issue was created (ISO 8601 format)",
    )
    body: str | None = Field(default=None, description="Issue description")
    assignees: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of assignee information",
    )

    def display_key(self) -> str:
        """Return formatted key for display."""
        return f"#{self.number}"

    def display_status(self) -> str:
        """Return normalized status string."""
        return self.state.upper()

    def is_open(self) -> bool:
        """Check if issue is open."""
        return self.state == "open"


class JiraWorkItem(BaseModel):
    """Jira Work Item model.

    Validates Jira issue data from acli CLI --json output.

    Attributes:
        key: Issue key (e.g., "PROJ-123")
        fields: Dict containing issue fields including:
            - summary: Issue title
            - status: Dict with 'name' key
            - priority: Dict with 'name' key
            - assignee: Dict with 'displayName' key (optional)
            - description: Issue description (optional)
        self: Issue URL (API endpoint)
    """

    model_config = ConfigDict(strict=True, validate_assignment=True)

    key: str = Field(
        ...,
        description="Issue key (e.g., PROJ-123)",
        pattern=r"^[A-Z][A-Z0-9]*-\d+$",
        min_length=3,
    )
    fields: dict[str, Any] = Field(
        ...,
        description="Issue fields including summary, status, priority",
    )
    self: HttpUrl = Field(..., description="Issue API URL")

    @property
    def summary(self) -> str:
        """Get the issue summary/title."""
        value = self.fields.get("summary", "")
        return str(value) if value is not None else ""

    @property
    def status(self) -> str:
        """Get the issue status name."""
        status_field = self.fields.get("status", {})
        return status_field.get("name", "Unknown") if isinstance(status_field, dict) else "Unknown"

    @property
    def priority(self) -> str:
        """Get the issue priority name."""
        priority_field = self.fields.get("priority", {})
        return priority_field.get("name", "None") if isinstance(priority_field, dict) else "None"

    @property
    def assignee(self) -> str | None:
        """Get the assignee display name."""
        assignee_field = self.fields.get("assignee")
        if isinstance(assignee_field, dict):
            return assignee_field.get("displayName")
        return None

    @property
    def url(self) -> str:
        """Get the browser URL for this issue."""
        # Convert API URL to browser URL
        url_str = str(self.self)
        return url_str.replace("/rest/api/2/issue/", "/browse/").rstrip("/")

    def display_key(self) -> str:
        """Return formatted key for display."""
        return self.key

    def display_status(self) -> str:
        """Return normalized status string."""
        status_name = self.status.upper()
        # Normalize common Jira statuses
        status_map = {
            "TO DO": "TODO",
            "IN PROGRESS": "IN PROGRESS",
            "DONE": "DONE",
            "BLOCKED": "BLOCKED",
            "CLOSED": "DONE",
            "RESOLVED": "DONE",
        }
        return status_map.get(status_name, status_name)

    def is_open(self) -> bool:
        """Check if work item is open/ongoing."""
        closed_statuses = {"done", "closed", "resolved"}
        return self.status.lower() not in closed_statuses
