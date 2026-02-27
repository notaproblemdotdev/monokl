"""Tests for Jira CLI adapter.

Tests the JiraAdapter class with mocked subprocess calls to verify
success and error handling without requiring actual acli installation.
"""

import json
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from monokl.exceptions import CLIAuthError
from monokl.exceptions import CLINotFoundError
from monokl.models import JiraWorkItem
from monokl.sources.jira._cli import JiraAdapter


@pytest.fixture
def jira_adapter():
    """Create a JiraAdapter instance for testing."""
    return JiraAdapter(base_url="https://company.atlassian.net")


@pytest.fixture
def sample_jira_issue():
    """Return a sample Jira issue dict as returned by acli."""
    return {
        "key": "PROJ-123",
        "fields": {
            "summary": "Implement user authentication",
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "assignee": {"displayName": "John Doe"},
        },
        "self": "https://company.atlassian.net/rest/api/2/issue/PROJ-123",
    }


@pytest.fixture
def sample_jira_issue2():
    """Return a second sample Jira issue dict."""
    return {
        "key": "PROJ-124",
        "fields": {
            "summary": "Fix navigation bug",
            "status": {"name": "To Do"},
            "priority": {"name": "Medium"},
            "assignee": {"displayName": "Jane Smith"},
        },
        "self": "https://company.atlassian.net/rest/api/2/issue/PROJ-124",
    }


@pytest.mark.asyncio
async def test_fetch_assigned_items_success(jira_adapter, sample_jira_issue, sample_jira_issue2):
    """Test fetching issues returns list of validated JiraWorkItems."""
    mock_issues = [sample_jira_issue, sample_jira_issue2]
    mock_output = json.dumps(mock_issues)

    with (
        patch("shutil.which", return_value="/usr/local/bin/acli"),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=create_mock_process(mock_output, 0),
        ),
    ):
        issues = await jira_adapter.fetch_assigned_items()

    assert len(issues) == 2
    assert all(isinstance(issue, JiraWorkItem) for issue in issues)

    # Verify first issue fields
    assert issues[0].key == "PROJ-123"
    assert issues[0].title == "Implement user authentication"
    assert issues[0].status == "In Progress"
    assert issues[0].priority == 4
    assert issues[0].assignee == "John Doe"
    assert issues[0].url == "https://company.atlassian.net/browse/PROJ-123"

    # Verify second issue fields
    assert issues[1].key == "PROJ-124"
    assert issues[1].title == "Fix navigation bug"
    assert issues[1].status == "To Do"
    assert issues[1].priority == 3

    # Verify helper methods
    assert issues[0].display_key() == "PROJ-123"
    assert issues[0].display_status() == "IN PROGRESS"
    assert issues[0].is_open() is True


@pytest.mark.asyncio
async def test_fetch_assigned_items_empty(jira_adapter):
    """Test fetching with empty result returns empty list."""
    mock_output = json.dumps([])

    with (
        patch("shutil.which", return_value="/usr/local/bin/acli"),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=create_mock_process(mock_output, 0),
        ),
    ):
        issues = await jira_adapter.fetch_assigned_items()

    assert issues == []
    assert isinstance(issues, list)


@pytest.mark.asyncio
async def test_fetch_assigned_items_not_installed(jira_adapter):
    """Test fetching when acli not installed raises CLINotFoundError."""
    with patch("shutil.which", return_value=None), pytest.raises(CLINotFoundError) as exc_info:
        await jira_adapter.fetch_assigned_items()

    assert "acli" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_assigned_items_auth_failure(jira_adapter):
    """Test fetching when not authenticated raises CLIAuthError."""
    mock_stderr = "Error: Not authenticated. Please run 'acli login'"

    with (
        patch("shutil.which", return_value="/usr/local/bin/acli"),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=create_mock_process("", 1, mock_stderr),
        ),
        pytest.raises(CLIAuthError) as exc_info,
    ):
        await jira_adapter.fetch_assigned_items()

    # Verify it's a CLIAuthError with the auth error message attribute
    assert exc_info.value.message == "Authentication failed. Please run the CLI's login command."
    # Verify the error message contains auth-related text
    assert "not authenticated" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_check_auth_success(jira_adapter):
    """Test check_auth returns True when authenticated."""
    mock_output = "john.doe@example.com"

    with (
        patch("shutil.which", return_value="/usr/local/bin/acli"),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=create_mock_process(mock_output, 0),
        ),
    ):
        result = await jira_adapter.check_auth()

    assert result is True


@pytest.mark.asyncio
async def test_check_auth_failure(jira_adapter):
    """Test check_auth returns False when not authenticated."""
    mock_stderr = "Error: Not authenticated"

    with (
        patch("shutil.which", return_value="/usr/local/bin/acli"),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=create_mock_process("", 1, mock_stderr),
        ),
    ):
        result = await jira_adapter.check_auth()

    assert result is False


@pytest.mark.asyncio
async def test_check_auth_not_installed(jira_adapter):
    """Test check_auth returns False when acli not installed."""
    with patch("shutil.which", return_value=None):
        result = await jira_adapter.check_auth()

    assert result is False


@pytest.mark.asyncio
async def test_fetch_with_custom_filters(jira_adapter, sample_jira_issue):
    """Test fetching with custom status and assignee filters."""
    mock_output = json.dumps([sample_jira_issue])

    with (
        patch("shutil.which", return_value="/usr/local/bin/acli"),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=create_mock_process(mock_output, 0),
        ) as mock_exec,
    ):
        issues = await jira_adapter.fetch_assigned_items(
            status_filter="In Progress",
            assignee="john.doe",
        )

    # Verify the command was called with correct arguments
    call_args = mock_exec.call_args
    cmd_list = call_args[0]

    assert "jira" in cmd_list
    assert "workitem" in cmd_list
    assert "search" in cmd_list
    assert "--json" in cmd_list
    assert "--jql" in cmd_list

    assert len(issues) == 1
    assert issues[0].key == "PROJ-123"


def create_mock_process(stdout: str, returncode: int, stderr: str = ""):
    """Create a mock asyncio subprocess.Process."""
    mock_proc = MagicMock()
    mock_proc.returncode = returncode

    # Create an async mock for communicate
    async_mock = AsyncMock()
    async_mock.return_value = (stdout.encode(), stderr.encode())
    mock_proc.communicate = async_mock

    return mock_proc
