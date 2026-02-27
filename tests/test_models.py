"""Comprehensive tests for Pydantic models.

Tests cover valid instantiation, validation errors, and helper methods
for all platform data models.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from monokl.models import GitHubIssue
from monokl.models import JiraWorkItem
from monokl.models import MergeRequest
from monokl.models import Priority
from monokl.models import PullRequest
from monokl.models import WorkItemStatus

# =============================================================================
# Fixtures - Valid sample data
# =============================================================================


@pytest.fixture
def valid_pr_data() -> dict[str, Any]:
    """Return valid GitHub PR data."""
    return {
        "number": 123,
        "title": "Add feature X",
        "state": "open",
        "author": {"login": "testuser"},
        "html_url": "https://github.com/test/repo/pull/123",
        "draft": False,
        "created_at": "2025-02-07T10:00:00Z",
        "body": "This PR adds feature X",
    }


@pytest.fixture
def valid_mr_data() -> dict[str, Any]:
    """Return valid GitLab MR data."""
    return {
        "iid": 456,
        "title": "Fix bug Y",
        "state": "opened",
        "author": {"name": "Test User", "username": "testuser"},
        "web_url": "https://gitlab.com/test/repo/-/merge_requests/456",
        "source_branch": "feature/fix-bug",
        "target_branch": "main",
        "draft": False,
        "created_at": "2025-02-07T11:00:00Z",
        "description": "This MR fixes bug Y",
    }


@pytest.fixture
def valid_issue_data() -> dict[str, Any]:
    """Return valid GitHub Issue data."""
    return {
        "number": 789,
        "title": "Issue description",
        "state": "open",
        "author": {"login": "testuser"},
        "html_url": "https://github.com/test/repo/issues/789",
        "labels": ["bug", "high-priority"],
        "created_at": "2025-02-07T09:00:00Z",
        "body": "Detailed issue description",
        "assignees": [{"login": "testuser"}],
    }


@pytest.fixture
def valid_jira_data() -> dict[str, Any]:
    """Return valid Jira issue data."""
    return {
        "key": "PROJ-123",
        "fields": {
            "summary": "Implement feature Z",
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "assignee": {"displayName": "Test User"},
            "description": "Detailed description",
        },
        "self": "https://jira.example.com/rest/api/2/issue/12345",
    }


# =============================================================================
# Valid Instantiation Tests
# =============================================================================


class TestPullRequestValid:
    """Tests for valid PullRequest instantiation."""

    def test_pull_request_valid(self, valid_pr_data: dict[str, Any]) -> None:
        """Create PR from valid data."""
        pr = PullRequest(**valid_pr_data)
        assert pr.number == 123
        assert pr.title == "Add feature X"
        assert pr.state == "open"
        assert pr.author == {"login": "testuser"}
        assert str(pr.html_url) == "https://github.com/test/repo/pull/123"
        assert pr.draft is False
        assert pr.created_at is not None
        assert pr.body == "This PR adds feature X"

    def test_pull_request_minimal(self) -> None:
        """Create PR with minimal required fields."""
        pr = PullRequest(
            number=1,
            title="Test",
            state="closed",
            author={"login": "user"},
            html_url="https://github.com/test/repo/pull/1",
        )
        assert pr.number == 1
        assert pr.draft is False
        assert pr.created_at is None
        assert pr.body is None

    @pytest.mark.parametrize(
        "state",
        ["open", "closed", "merged"],
    )
    def test_pull_request_valid_states(self, state: str) -> None:
        """Test all valid PR states."""
        pr = PullRequest(
            number=1,
            title="Test",
            state=state,
            author={"login": "user"},
            html_url="https://github.com/test/repo/pull/1",
        )
        assert pr.state == state


class TestMergeRequestValid:
    """Tests for valid MergeRequest instantiation."""

    def test_merge_request_valid(self, valid_mr_data: dict[str, Any]) -> None:
        """Create MR from valid data."""
        mr = MergeRequest(**valid_mr_data)
        assert mr.iid == 456
        assert mr.title == "Fix bug Y"
        assert mr.state == "opened"
        assert mr.author == {"name": "Test User", "username": "testuser"}
        assert str(mr.web_url) == "https://gitlab.com/test/repo/-/merge_requests/456"
        assert mr.source_branch == "feature/fix-bug"
        assert mr.target_branch == "main"
        assert mr.draft is False

    @pytest.mark.parametrize(
        "state",
        ["opened", "closed", "merged", "locked"],
    )
    def test_merge_request_valid_states(self, state: str) -> None:
        """Test all valid MR states."""
        mr = MergeRequest(
            iid=1,
            title="Test",
            state=state,
            author={"name": "User", "username": "user"},
            web_url="https://gitlab.com/test/repo/-/merge_requests/1",
            source_branch="feature",
            target_branch="main",
        )
        assert mr.state == state


class TestGitHubIssueValid:
    """Tests for valid GitHubIssue instantiation."""

    def test_github_issue_valid(self, valid_issue_data: dict[str, Any]) -> None:
        """Create issue from valid data."""
        issue = GitHubIssue(**valid_issue_data)
        assert issue.number == 789
        assert issue.title == "Issue description"
        assert issue.state == "open"
        assert issue.author == {"login": "testuser"}
        assert str(issue.html_url) == "https://github.com/test/repo/issues/789"
        assert issue.labels == ["bug", "high-priority"]
        assert len(issue.assignees) == 1

    def test_github_issue_minimal(self) -> None:
        """Create issue with minimal fields."""
        issue = GitHubIssue(
            number=1,
            title="Test",
            state="closed",
            author={"login": "user"},
            html_url="https://github.com/test/repo/issues/1",
        )
        assert issue.labels == []
        assert issue.assignees == []

    @pytest.mark.parametrize(
        "state",
        ["open", "closed"],
    )
    def test_github_issue_valid_states(self, state: str) -> None:
        """Test all valid issue states."""
        issue = GitHubIssue(
            number=1,
            title="Test",
            state=state,
            author={"login": "user"},
            html_url="https://github.com/test/repo/issues/1",
        )
        assert issue.state == state


class TestJiraWorkItemValid:
    """Tests for valid JiraWorkItem instantiation."""

    def test_jira_work_item_valid(self, valid_jira_data: dict[str, Any]) -> None:
        """Create Jira item from valid data."""
        jira = JiraWorkItem(**valid_jira_data)
        assert jira.key == "PROJ-123"
        assert jira.summary == "Implement feature Z"
        assert jira.status == "In Progress"
        assert jira.priority == "High"
        assert jira.assignee == "Test User"
        assert str(jira.self) == "https://jira.example.com/rest/api/2/issue/12345"

    @pytest.mark.parametrize(
        "key",
        ["PROJ-1", "ABC-123", "TEAM-9999", "MYPROJ-456"],
    )
    def test_jira_valid_keys(self, key: str) -> None:
        """Test various valid Jira key formats."""
        jira = JiraWorkItem(
            key=key,
            fields={"summary": "Test"},
            self="https://jira.example.com/rest/api/2/issue/1",
        )
        assert jira.key == key

    def test_jira_without_optional_fields(self) -> None:
        """Create Jira item without optional fields."""
        jira = JiraWorkItem(
            key="TEST-1",
            fields={"summary": "Test"},
            self="https://jira.example.com/rest/api/2/issue/1",
        )
        assert jira.summary == "Test"
        assert jira.status == "Unknown"
        assert jira.priority == "None"
        assert jira.assignee is None


# =============================================================================
# Validation Error Tests
# =============================================================================


class TestPullRequestValidation:
    """Tests for PullRequest validation errors."""

    def test_pull_request_missing_required(self) -> None:
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError):
            PullRequest(
                number=123,
                # Missing title
                state="open",
                author={"login": "user"},
                html_url="https://github.com/test/repo/pull/123",
            )

    def test_pull_request_invalid_state(self) -> None:
        """Invalid state value should raise ValidationError."""
        with pytest.raises(ValidationError):
            PullRequest(
                number=123,
                title="Test",
                state="invalid_state",
                author={"login": "user"},
                html_url="https://github.com/test/repo/pull/123",
            )

    def test_pull_request_invalid_number(self) -> None:
        """Zero or negative number should raise ValidationError."""
        with pytest.raises(ValidationError):
            PullRequest(
                number=0,
                title="Test",
                state="open",
                author={"login": "user"},
                html_url="https://github.com/test/repo/pull/1",
            )

    def test_pull_request_empty_title(self) -> None:
        """Empty title should raise ValidationError."""
        with pytest.raises(ValidationError):
            PullRequest(
                number=123,
                title="",
                state="open",
                author={"login": "user"},
                html_url="https://github.com/test/repo/pull/123",
            )


class TestMergeRequestValidation:
    """Tests for MergeRequest validation errors."""

    def test_merge_request_invalid_state(self) -> None:
        """Invalid state value should raise ValidationError."""
        with pytest.raises(ValidationError):
            MergeRequest(
                iid=456,
                title="Test",
                state="invalid_state",
                author={"name": "User", "username": "user"},
                web_url="https://gitlab.com/test/repo/-/merge_requests/456",
                source_branch="feature",
                target_branch="main",
            )


class TestGitHubIssueValidation:
    """Tests for GitHubIssue validation errors."""

    def test_issue_invalid_state(self) -> None:
        """Invalid state should raise ValidationError."""
        with pytest.raises(ValidationError):
            GitHubIssue(
                number=789,
                title="Test",
                state="merged",  # Issues don't have merged state
                author={"login": "user"},
                html_url="https://github.com/test/repo/issues/789",
            )


class TestJiraWorkItemValidation:
    """Tests for JiraWorkItem validation errors."""

    def test_jira_invalid_key_no_hyphen(self) -> None:
        """Key without hyphen should raise ValidationError."""
        with pytest.raises(ValidationError):
            JiraWorkItem(
                key="INVALIDKEY",
                fields={"summary": "Test"},
                self="https://jira.example.com/rest/api/2/issue/1",
            )

    def test_jira_invalid_key_lowercase(self) -> None:
        """Key starting with lowercase should raise ValidationError."""
        with pytest.raises(ValidationError):
            JiraWorkItem(
                key="proj-123",
                fields={"summary": "Test"},
                self="https://jira.example.com/rest/api/2/issue/1",
            )

    def test_jira_key_starts_with_number(self) -> None:
        """Key starting with number should raise ValidationError."""
        with pytest.raises(ValidationError):
            JiraWorkItem(
                key="1PROJ-123",
                fields={"summary": "Test"},
                self="https://jira.example.com/rest/api/2/issue/1",
            )


class TestUrlValidation:
    """Tests for URL validation across all models."""

    def test_pr_invalid_url(self) -> None:
        """Malformed URL should raise ValidationError."""
        with pytest.raises(ValidationError):
            PullRequest(
                number=123,
                title="Test",
                state="open",
                author={"login": "user"},
                html_url="not-a-valid-url",
            )

    def test_mr_invalid_url(self) -> None:
        """Malformed URL should raise ValidationError."""
        with pytest.raises(ValidationError):
            MergeRequest(
                iid=456,
                title="Test",
                state="opened",
                author={"name": "User", "username": "user"},
                web_url="not-a-url",
                source_branch="feature",
                target_branch="main",
            )

    def test_jira_invalid_url(self) -> None:
        """Malformed URL should raise ValidationError."""
        with pytest.raises(ValidationError):
            JiraWorkItem(
                key="PROJ-123",
                fields={"summary": "Test"},
                self="invalid-url",
            )


class TestDatetimeValidation:
    """Tests for datetime validation."""

    def test_pr_invalid_datetime(self) -> None:
        """Non-ISO datetime string should raise ValidationError."""
        with pytest.raises(ValidationError):
            PullRequest(
                number=123,
                title="Test",
                state="open",
                author={"login": "user"},
                html_url="https://github.com/test/repo/pull/123",
                created_at="not-a-date",
            )

    def test_mr_invalid_datetime(self) -> None:
        """Non-ISO datetime string should raise ValidationError."""
        with pytest.raises(ValidationError):
            MergeRequest(
                iid=456,
                title="Test",
                state="opened",
                author={"name": "User", "username": "user"},
                web_url="https://gitlab.com/test/repo/-/merge_requests/456",
                source_branch="feature",
                target_branch="main",
                created_at="invalid-datetime",
            )


# =============================================================================
# Helper Method Tests
# =============================================================================


class TestDisplayKeyFormats:
    """Tests for display_key() helper method."""

    def test_pr_display_key(self) -> None:
        """PR display_key should return #number format."""
        pr = PullRequest(
            number=123,
            title="Test",
            state="open",
            author={"login": "user"},
            html_url="https://github.com/test/repo/pull/123",
        )
        assert pr.display_key() == "#123"

    def test_mr_display_key(self) -> None:
        """MR display_key should return !iid format."""
        mr = MergeRequest(
            iid=456,
            title="Test",
            state="opened",
            author={"name": "User", "username": "user"},
            web_url="https://gitlab.com/test/repo/-/merge_requests/456",
            source_branch="feature",
            target_branch="main",
        )
        assert mr.display_key() == "!456"

    def test_issue_display_key(self) -> None:
        """Issue display_key should return #number format."""
        issue = GitHubIssue(
            number=789,
            title="Test",
            state="open",
            author={"login": "user"},
            html_url="https://github.com/test/repo/issues/789",
        )
        assert issue.display_key() == "#789"

    def test_jira_display_key(self) -> None:
        """Jira display_key should return key as-is."""
        jira = JiraWorkItem(
            key="PROJ-123",
            fields={"summary": "Test"},
            self="https://jira.example.com/rest/api/2/issue/1",
        )
        assert jira.display_key() == "PROJ-123"


class TestIsOpenLogic:
    """Tests for is_open() helper method."""

    def test_pr_is_open_open(self) -> None:
        """Open PR should return True."""
        pr = PullRequest(
            number=123,
            title="Test",
            state="open",
            author={"login": "user"},
            html_url="https://github.com/test/repo/pull/123",
        )
        assert pr.is_open() is True

    def test_pr_is_open_closed(self) -> None:
        """Closed PR should return False."""
        pr = PullRequest(
            number=123,
            title="Test",
            state="closed",
            author={"login": "user"},
            html_url="https://github.com/test/repo/pull/123",
        )
        assert pr.is_open() is False

    def test_pr_is_open_merged(self) -> None:
        """Merged PR should return False."""
        pr = PullRequest(
            number=123,
            title="Test",
            state="merged",
            author={"login": "user"},
            html_url="https://github.com/test/repo/pull/123",
        )
        assert pr.is_open() is False

    def test_mr_is_open_opened(self) -> None:
        """Opened MR should return True."""
        mr = MergeRequest(
            iid=456,
            title="Test",
            state="opened",
            author={"name": "User", "username": "user"},
            web_url="https://gitlab.com/test/repo/-/merge_requests/456",
            source_branch="feature",
            target_branch="main",
        )
        assert mr.is_open() is True

    def test_mr_is_open_closed(self) -> None:
        """Closed MR should return False."""
        mr = MergeRequest(
            iid=456,
            title="Test",
            state="closed",
            author={"name": "User", "username": "user"},
            web_url="https://gitlab.com/test/repo/-/merge_requests/456",
            source_branch="feature",
            target_branch="main",
        )
        assert mr.is_open() is False

    def test_mr_is_open_merged(self) -> None:
        """Merged MR should return False."""
        mr = MergeRequest(
            iid=456,
            title="Test",
            state="merged",
            author={"name": "User", "username": "user"},
            web_url="https://gitlab.com/test/repo/-/merge_requests/456",
            source_branch="feature",
            target_branch="main",
        )
        assert mr.is_open() is False

    def test_issue_is_open_open(self) -> None:
        """Open issue should return True."""
        issue = GitHubIssue(
            number=789,
            title="Test",
            state="open",
            author={"login": "user"},
            html_url="https://github.com/test/repo/issues/789",
        )
        assert issue.is_open() is True

    def test_issue_is_open_closed(self) -> None:
        """Closed issue should return False."""
        issue = GitHubIssue(
            number=789,
            title="Test",
            state="closed",
            author={"login": "user"},
            html_url="https://github.com/test/repo/issues/789",
        )
        assert issue.is_open() is False

    @pytest.mark.parametrize(
        "status,expected",
        [
            ("In Progress", True),
            ("To Do", True),
            ("Done", False),
            ("Closed", False),
            ("Resolved", False),
        ],
    )
    def test_jira_is_open(self, status: str, expected: bool) -> None:
        """Jira is_open should handle various statuses."""
        jira = JiraWorkItem(
            key="PROJ-123",
            fields={"summary": "Test", "status": {"name": status}},
            self="https://jira.example.com/rest/api/2/issue/1",
        )
        assert jira.is_open() is expected


class TestDisplayStatus:
    """Tests for display_status() helper method."""

    def test_pr_display_status(self) -> None:
        """PR display_status should return uppercase state."""
        pr = PullRequest(
            number=123,
            title="Test",
            state="open",
            author={"login": "user"},
            html_url="https://github.com/test/repo/pull/123",
        )
        assert pr.display_status() == "OPEN"

    def test_jira_display_status_normalization(self) -> None:
        """Jira display_status should normalize common statuses."""
        jira = JiraWorkItem(
            key="PROJ-123",
            fields={"summary": "Test", "status": {"name": "To Do"}},
            self="https://jira.example.com/rest/api/2/issue/1",
        )
        assert jira.display_status() == "TODO"

    def test_jira_display_status_in_progress(self) -> None:
        """Jira display_status should handle In Progress."""
        jira = JiraWorkItem(
            key="PROJ-123",
            fields={"summary": "Test", "status": {"name": "In Progress"}},
            self="https://jira.example.com/rest/api/2/issue/1",
        )
        assert jira.display_status() == "IN PROGRESS"


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for enumeration classes."""

    def test_work_item_status_values(self) -> None:
        """WorkItemStatus should have expected values."""
        assert WorkItemStatus.TODO == "todo"
        assert WorkItemStatus.IN_PROGRESS == "in_progress"
        assert WorkItemStatus.DONE == "done"
        assert WorkItemStatus.BLOCKED == "blocked"

    def test_priority_values(self) -> None:
        """Priority should have expected values."""
        assert Priority.LOWEST == "lowest"
        assert Priority.LOW == "low"
        assert Priority.MEDIUM == "medium"
        assert Priority.HIGH == "high"
        assert Priority.HIGHEST == "highest"
