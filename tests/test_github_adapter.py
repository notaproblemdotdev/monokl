"""Tests for GitHub CLI adapter error propagation."""

from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from monokl.exceptions import CLIAuthError
from monokl.sources.github._cli import GitHubAdapter


@pytest.mark.asyncio
async def test_fetch_assigned_issues_raises_auth_error() -> None:
    """Auth failures should propagate so callers can mark source as failed."""
    adapter = GitHubAdapter()

    with (
        patch("shutil.which", return_value="/usr/local/bin/gh"),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=_mock_process("", 1, "not logged in"),
        ),
        pytest.raises(CLIAuthError),
    ):
        await adapter.fetch_assigned_issues()


def _mock_process(stdout: str, returncode: int, stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    return proc
