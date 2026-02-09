"""Tests for GitLab CLI adapter.

Comprehensive tests for GitLabAdapter including success cases,
error handling, and authentication checks.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from monocli.adapters.gitlab import GitLabAdapter
from monocli.exceptions import CLIAuthError, CLINotFoundError
from monocli.models import MergeRequest


class TestGitLabAdapter:
    """Tests for the GitLabAdapter class."""

    def test_adapter_init(self) -> None:
        """Test proper initialization of GitLabAdapter."""
        adapter = GitLabAdapter()

        assert adapter.cli_name == "glab"
        assert adapter._available is None

    def test_is_available_installed(self) -> None:
        """Test is_available returns True when glab is installed."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            assert adapter.is_available() is True
            assert adapter._available is True

    def test_is_available_not_installed(self) -> None:
        """Test is_available returns False when glab is not installed."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            assert adapter.is_available() is False
            assert adapter._available is False

    def test_is_available_cached(self) -> None:
        """Test is_available caches the result."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            # First call should check
            result1 = adapter.is_available()
            assert mock_which.call_count == 1

            # Second call should use cache
            result2 = adapter.is_available()
            assert mock_which.call_count == 1  # Not called again

            assert result1 == result2


class TestFetchAssignedMRs:
    """Tests for fetch_assigned_mrs method."""

    @pytest.mark.asyncio
    async def test_fetch_assigned_mrs_success(self) -> None:
        """Test successful fetch of merge requests."""
        adapter = GitLabAdapter()

        # Sample MR data from glab --json output
        sample_mrs = [
            {
                "iid": 123,
                "title": "Fix authentication bug",
                "state": "opened",
                "author": {"name": "John Doe", "username": "johndoe"},
                "web_url": "https://gitlab.com/org/repo/-/merge_requests/123",
                "source_branch": "feature/auth-fix",
                "target_branch": "main",
                "created_at": "2024-01-15T10:30:00Z",
                "draft": False,
            },
            {
                "iid": 124,
                "title": "Update documentation",
                "state": "opened",
                "author": {"name": "Jane Smith", "username": "janesmith"},
                "web_url": "https://gitlab.com/org/repo/-/merge_requests/124",
                "source_branch": "feature/docs-update",
                "target_branch": "main",
                "created_at": "2024-01-14T15:45:00Z",
                "draft": True,
            },
        ]

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        json.dumps(sample_mrs).encode(),
                        b"",
                    )
                )
                mock_exec.return_value = mock_proc

                mrs = await adapter.fetch_assigned_mrs(group="test-group")

        assert len(mrs) == 2
        assert all(isinstance(mr, MergeRequest) for mr in mrs)

        # Verify first MR
        assert mrs[0].iid == 123
        assert mrs[0].title == "Fix authentication bug"
        assert mrs[0].state == "opened"
        assert mrs[0].author["username"] == "johndoe"
        assert str(mrs[0].web_url) == "https://gitlab.com/org/repo/-/merge_requests/123"
        assert mrs[0].draft is False

        # Verify second MR
        assert mrs[1].iid == 124
        assert mrs[1].title == "Update documentation"
        assert mrs[1].draft is True

    @pytest.mark.asyncio
    async def test_fetch_assigned_mrs_empty(self) -> None:
        """Test fetch returns empty list when no MRs found."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        json.dumps([]).encode(),
                        b"",
                    )
                )
                mock_exec.return_value = mock_proc

                mrs = await adapter.fetch_assigned_mrs(group="test-group")

        assert mrs == []

    @pytest.mark.asyncio
    async def test_fetch_assigned_mrs_not_installed(self) -> None:
        """Test CLINotFoundError when glab is not installed."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            with pytest.raises(CLINotFoundError) as exc_info:
                await adapter.fetch_assigned_mrs(group="test-group")

        assert exc_info.value.cli_name == "glab"

    @pytest.mark.asyncio
    async def test_fetch_assigned_mrs_auth_failure(self) -> None:
        """Test CLIAuthError when authentication fails."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 1
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        b"",
                        b"not logged in",
                    )
                )
                mock_exec.return_value = mock_proc

                with pytest.raises(CLIAuthError) as exc_info:
                    await adapter.fetch_assigned_mrs(group="test-group")

        assert "not logged in" in exc_info.value.stderr.lower()

    @pytest.mark.asyncio
    async def test_fetch_assigned_mrs_with_state_filter(self) -> None:
        """Test fetch with different state filters."""
        adapter = GitLabAdapter()

        sample_mrs = [
            {
                "iid": 125,
                "title": "Merged feature",
                "state": "merged",
                "author": {"name": "Bob", "username": "bob"},
                "web_url": "https://gitlab.com/org/repo/-/merge_requests/125",
                "source_branch": "feature/old",
                "target_branch": "main",
                "created_at": "2024-01-10T09:00:00Z",
                "draft": False,
            }
        ]

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        json.dumps(sample_mrs).encode(),
                        b"",
                    )
                )
                mock_exec.return_value = mock_proc

                # Fetch merged MRs
                mrs = await adapter.fetch_assigned_mrs(group="test-group", state="merged")

        assert len(mrs) == 1
        assert mrs[0].state == "merged"

        # Verify the command was called with --merged flag
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        cmd_list = call_args[0]
        assert "--merged" in cmd_list

    @pytest.mark.asyncio
    async def test_fetch_assigned_mrs_with_author_filter(self) -> None:
        """Test fetch with custom author filter."""
        adapter = GitLabAdapter()

        sample_mrs = [
            {
                "iid": 126,
                "title": "Team member MR",
                "state": "opened",
                "author": {"name": "Alice", "username": "alice"},
                "web_url": "https://gitlab.com/org/repo/-/merge_requests/126",
                "source_branch": "feature/alice",
                "target_branch": "main",
                "created_at": "2024-01-16T11:00:00Z",
                "draft": False,
            }
        ]

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        json.dumps(sample_mrs).encode(),
                        b"",
                    )
                )
                mock_exec.return_value = mock_proc

                # Fetch MRs by specific author
                mrs = await adapter.fetch_assigned_mrs(group="test-group", author="alice")

        assert len(mrs) == 1
        assert mrs[0].author["username"] == "alice"

        # Verify the command was called with correct args
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        cmd_list = call_args[0]
        assert "--author" in cmd_list
        assert "alice" in cmd_list

    @pytest.mark.asyncio
    async def test_fetch_assigned_mrs_validates_fields(self) -> None:
        """Test that MR data is properly validated into Pydantic models."""
        adapter = GitLabAdapter()

        sample_mr = {
            "iid": 127,
            "title": "Test MR",
            "state": "opened",
            "author": {"name": "Test", "username": "test"},
            "web_url": "https://gitlab.com/org/repo/-/merge_requests/127",
            "source_branch": "feature/test",
            "target_branch": "main",
            "created_at": "2024-01-16T12:00:00Z",
            "draft": False,
        }

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        json.dumps([sample_mr]).encode(),
                        b"",
                    )
                )
                mock_exec.return_value = mock_proc

                mrs = await adapter.fetch_assigned_mrs(group="test-group")

        assert len(mrs) == 1
        mr = mrs[0]

        # Verify helper methods work
        assert mr.display_key() == "!127"
        assert mr.display_status() == "OPENED"
        assert mr.is_open() is True


class TestCheckAuth:
    """Tests for check_auth method."""

    @pytest.mark.asyncio
    async def test_check_auth_success(self) -> None:
        """Test check_auth returns True when authenticated."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        b"Logged in to gitlab.com as user",
                        b"",
                    )
                )
                mock_exec.return_value = mock_proc

                is_authenticated = await adapter.check_auth()

        assert is_authenticated is True

    @pytest.mark.asyncio
    async def test_check_auth_failure(self) -> None:
        """Test check_auth returns False when not authenticated."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 1
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        b"",
                        b"not logged in",
                    )
                )
                mock_exec.return_value = mock_proc

                is_authenticated = await adapter.check_auth()

        assert is_authenticated is False

    @pytest.mark.asyncio
    async def test_check_auth_not_installed(self) -> None:
        """Test check_auth returns False when glab not installed."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            is_authenticated = await adapter.check_auth()

        assert is_authenticated is False

    @pytest.mark.asyncio
    async def test_check_auth_handles_cli_auth_error(self) -> None:
        """Test check_auth handles CLIAuthError gracefully."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 1
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        b"",
                        b"authentication failed",
                    )
                )
                mock_exec.return_value = mock_proc

                is_authenticated = await adapter.check_auth()

        assert is_authenticated is False

    @pytest.mark.asyncio
    async def test_check_auth_handles_unauthorized(self) -> None:
        """Test check_auth handles 401 unauthorized gracefully."""
        adapter = GitLabAdapter()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/glab"

            with patch(
                "asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 1
                mock_proc.communicate = AsyncMock(
                    return_value=(
                        b"",
                        b"401 unauthorized",
                    )
                )
                mock_exec.return_value = mock_proc

                is_authenticated = await adapter.check_auth()

        assert is_authenticated is False
