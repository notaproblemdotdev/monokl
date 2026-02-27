"""Tests for Azure DevOps API adapter.

Comprehensive tests for AzureDevOpsAPIAdapter including success cases,
error handling, and authentication checks.
"""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from monokl.models import AzureDevOpsPieceOfWork
from monokl.models import AzureDevOpsPullRequest
from monokl.sources.azuredevops._api import AzureDevOpsAPIAdapter


class TestAzureDevOpsAPIAdapter:
    """Tests for the AzureDevOpsAPIAdapter class."""

    def test_adapter_init(self) -> None:
        """Test proper initialization of AzureDevOpsAPIAdapter."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="test-pat-token",
        )

        assert adapter.organization == "myorg"
        assert adapter.project == "MyProject"
        assert adapter.token == "test-pat-token"
        assert adapter._base_url == "https://dev.azure.com/myorg"

    def test_headers_include_auth(self) -> None:
        """Test that headers include authentication."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="test-token",
        )

        headers = adapter._headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert "Content-Type" in headers


class TestCheckAuth:
    """Tests for check_auth method."""

    @pytest.mark.asyncio
    async def test_check_auth_success(self) -> None:
        """Test check_auth returns True when token is valid."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="valid-token",
        )

        mock_response = MagicMock()
        mock_response.status = 200

        mock_get = MagicMock()
        mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await adapter.check_auth()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_auth_failure(self) -> None:
        """Test check_auth returns False when token is invalid."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="invalid-token",
        )

        mock_response = MagicMock()
        mock_response.status = 401

        mock_get = MagicMock()
        mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await adapter.check_auth()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_auth_handles_exception(self) -> None:
        """Test check_auth returns False on network error."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="test-token",
        )

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Network error")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await adapter.check_auth()

        assert result is False


class TestFetchPullRequests:
    """Tests for fetch_pull_requests method."""

    @pytest.mark.asyncio
    async def test_fetch_pull_requests_success(self) -> None:
        """Test successful fetch of pull requests."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="test-token",
        )

        sample_prs = {
            "value": [
                {
                    "pullRequestId": 123,
                    "title": "Fix authentication bug",
                    "status": "active",
                    "createdBy": {"displayName": "John Doe", "uniqueName": "john@example.com"},
                    "repository": {"id": "repo-123", "name": "myrepo"},
                    "sourceRefName": "refs/heads/feature/auth-fix",
                    "targetRefName": "refs/heads/main",
                    "creationDate": "2024-01-15T10:30:00Z",
                    "isDraft": False,
                },
                {
                    "pullRequestId": 124,
                    "title": "Update documentation",
                    "status": "active",
                    "createdBy": {"displayName": "Jane Smith"},
                    "repository": {"id": "repo-123", "name": "myrepo"},
                    "sourceRefName": "refs/heads/docs/update",
                    "targetRefName": "refs/heads/main",
                    "creationDate": "2024-01-14T15:45:00Z",
                    "isDraft": True,
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_prs)

        mock_get = MagicMock()
        mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            prs = await adapter.fetch_pull_requests()

        assert len(prs) == 2
        assert all(isinstance(pr, AzureDevOpsPullRequest) for pr in prs)

        assert prs[0].pullRequestId == 123
        assert prs[0].title == "Fix authentication bug"
        assert prs[0].status == "active"
        assert prs[0].isDraft is False
        assert prs[0].is_open() is True

        assert prs[1].pullRequestId == 124
        assert prs[1].isDraft is True

    @pytest.mark.asyncio
    async def test_fetch_pull_requests_empty(self) -> None:
        """Test fetch returns empty list when no PRs found."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="test-token",
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"value": []})

        mock_get = MagicMock()
        mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            prs = await adapter.fetch_pull_requests()

        assert prs == []

    @pytest.mark.asyncio
    async def test_fetch_pull_requests_api_error(self) -> None:
        """Test fetch returns empty list on API error."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="test-token",
        )

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        mock_get = MagicMock()
        mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            prs = await adapter.fetch_pull_requests()

        assert prs == []


class TestFetchWorkItems:
    """Tests for fetch_work_items method."""

    @pytest.mark.asyncio
    async def test_fetch_work_items_success(self) -> None:
        """Test successful fetch of work items."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="test-token",
        )

        wiql_response = {
            "workItems": [
                {"id": 1001},
                {"id": 1002},
            ]
        }

        work_items_response = {
            "value": [
                {
                    "id": 1001,
                    "fields": {
                        "System.Title": "Implement feature X",
                        "System.State": "In Progress",
                        "System.AssignedTo": {"displayName": "John Doe"},
                    },
                    "url": "https://dev.azure.com/myorg/_apis/wit/workItems/1001",
                },
                {
                    "id": 1002,
                    "fields": {
                        "System.Title": "Fix bug Y",
                        "System.State": "To Do",
                    },
                    "url": "https://dev.azure.com/myorg/_apis/wit/workItems/1002",
                },
            ]
        }

        wiql_mock_response = MagicMock()
        wiql_mock_response.status = 200
        wiql_mock_response.json = AsyncMock(return_value=wiql_response)

        items_mock_response = MagicMock()
        items_mock_response.status = 200
        items_mock_response.json = AsyncMock(return_value=work_items_response)

        call_count = 0

        def create_context_manager(mock_resp):
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=mock_resp)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        def get_post_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return create_context_manager(wiql_mock_response)
            return create_context_manager(items_mock_response)

        mock_session = MagicMock()
        mock_session.post = get_post_side_effect
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            items = await adapter.fetch_work_items()

        assert len(items) == 2
        assert all(isinstance(item, AzureDevOpsPieceOfWork) for item in items)

    @pytest.mark.asyncio
    async def test_fetch_work_items_empty(self) -> None:
        """Test fetch returns empty list when no work items found."""
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="test-token",
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"workItems": []})

        mock_post = MagicMock()
        mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            items = await adapter.fetch_work_items()

        assert items == []


class TestModels:
    """Tests for Azure DevOps Pydantic models."""

    def test_pull_request_model_validation(self) -> None:
        """Test AzureDevOpsPullRequest model validation."""
        pr = AzureDevOpsPullRequest(
            pullRequestId=123,
            title="Test PR",
            status="active",
            createdBy={"displayName": "Test User"},
            repository={"id": "repo-1", "name": "testrepo"},
            sourceRefName="refs/heads/feature/test",
            targetRefName="refs/heads/main",
            creationDate="2024-01-15T10:30:00Z",
            isDraft=False,
        )

        assert pr.pullRequestId == 123
        assert pr.title == "Test PR"
        assert pr.status == "active"
        assert pr.display_key() == "#123"
        assert pr.display_status() == "ACTIVE"
        assert pr.is_open() is True

    def test_pull_request_status_states(self) -> None:
        """Test PR status states."""
        active_pr = AzureDevOpsPullRequest(
            pullRequestId=1,
            title="Active",
            status="active",
            createdBy={},
            repository={},
            sourceRefName="refs/heads/a",
            targetRefName="refs/heads/b",
        )
        assert active_pr.is_open() is True

        abandoned_pr = AzureDevOpsPullRequest(
            pullRequestId=2,
            title="Abandoned",
            status="abandoned",
            createdBy={},
            repository={},
            sourceRefName="refs/heads/a",
            targetRefName="refs/heads/b",
        )
        assert abandoned_pr.is_open() is False

        completed_pr = AzureDevOpsPullRequest(
            pullRequestId=3,
            title="Completed",
            status="completed",
            createdBy={},
            repository={},
            sourceRefName="refs/heads/a",
            targetRefName="refs/heads/b",
        )
        assert completed_pr.is_open() is False

    def test_work_item_model_validation(self) -> None:
        """Test AzureDevOpsPieceOfWork model validation."""
        wi = AzureDevOpsPieceOfWork(
            id=456,
            fields={
                "System.Title": "Test Work Item",
                "System.State": "In Progress",
                "System.AssignedTo": {"displayName": "John Doe"},
                "Microsoft.VSTS.Common.Priority": 2,
            },
            url="https://dev.azure.com/org/_apis/wit/workItems/456",
        )

        assert wi.id == 456
        assert wi.title == "Test Work Item"
        assert wi.status == "In Progress"
        assert wi.assignee == "John Doe"
        assert wi.priority == 2
        assert wi.display_key() == "#456"
        assert wi.is_open() is True

    def test_work_item_closed_states(self) -> None:
        """Test work item closed states."""
        closed_wi = AzureDevOpsPieceOfWork(
            id=1,
            fields={"System.Title": "Closed", "System.State": "Closed"},
            url="url",
        )
        assert closed_wi.is_open() is False

        done_wi = AzureDevOpsPieceOfWork(
            id=2,
            fields={"System.Title": "Done", "System.State": "Done"},
            url="url",
        )
        assert done_wi.is_open() is False

        removed_wi = AzureDevOpsPieceOfWork(
            id=3,
            fields={"System.Title": "Removed", "System.State": "Removed"},
            url="url",
        )
        assert removed_wi.is_open() is False

    def test_work_item_missing_optional_fields(self) -> None:
        """Test work item with missing optional fields."""
        wi = AzureDevOpsPieceOfWork(
            id=100,
            fields={},
            url="url",
        )

        assert wi.title == ""
        assert wi.status == "Unknown"
        assert wi.assignee is None
        assert wi.priority is None
