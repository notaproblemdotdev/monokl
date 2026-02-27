"""Tests for async subprocess utilities."""

import asyncio

import pytest

from monokl.async_utils import CLIAdapter
from monokl.async_utils import _subprocess_semaphore
from monokl.async_utils import run_cli_command
from monokl.exceptions import CLIError
from monokl.exceptions import CLINotFoundError


class TestConcurrentSubprocesses:
    """Tests for concurrent subprocess execution with semaphore protection."""

    @pytest.mark.asyncio
    async def test_concurrent_subprocesses_no_race_condition(self):
        """Test that concurrent subprocess calls don't cause race conditions.

        This test runs 5 concurrent echo commands to verify that the semaphore
        prevents the asyncio InvalidStateError that can occur with concurrent
        subprocess transport cleanup.
        """
        # Run multiple echo commands concurrently
        tasks = [run_cli_command(["echo", f"test{i}"], check=False) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed without exceptions
        assert len(results) == 5
        for i, result in enumerate(results):
            assert not isinstance(result, BaseException), f"Task {i} failed: {result}"
            assert isinstance(result, tuple)
            assert result[0] == f"test{i}"

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_execution(self):
        """Test that semaphore is configured with correct value."""
        # Initial value should be 3 (max concurrent subprocesses)
        assert _subprocess_semaphore._value == 3


class TestRunCliCommand:
    """Tests for run_cli_command function."""

    @pytest.mark.asyncio
    async def test_run_simple_command(self):
        """Test running a simple echo command."""
        stdout, stderr = await run_cli_command(["echo", "hello"])
        assert stdout == "hello"

    @pytest.mark.asyncio
    async def test_run_with_multiple_args(self):
        """Test command with multiple arguments."""
        stdout, stderr = await run_cli_command(["echo", "hello", "world"])
        assert stdout == "hello world"

    @pytest.mark.asyncio
    async def test_run_invalid_command_raises_not_found(self):
        """Test that non-existent command raises CLINotFoundError."""
        with pytest.raises(CLINotFoundError) as exc_info:
            await run_cli_command(["definitely_not_a_real_command_12345"])
        assert "definitely_not_a_real_command_12345" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_failing_command_raises_error(self):
        """Test that failing command raises CLIError."""
        with pytest.raises(CLIError) as exc_info:
            await run_cli_command(["python", "-c", "import sys; sys.exit(1)"])
        assert exc_info.value.returncode == 1

    @pytest.mark.asyncio
    async def test_run_without_check_does_not_raise(self):
        """Test that check=False prevents exception on failure."""
        stdout, stderr = await run_cli_command(
            ["python", "-c", "import sys; sys.exit(1)"], check=False
        )
        # Should not raise, but stdout might be empty
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)

    @pytest.mark.asyncio
    async def test_run_with_timeout(self):
        """Test that timeout parameter works."""
        # This should complete quickly
        stdout, stderr = await run_cli_command(["echo", "hi"], timeout=5.0)
        assert stdout == "hi"

    @pytest.mark.asyncio
    async def test_run_timeout_raises(self):
        """Test that slow command raises TimeoutError."""
        with pytest.raises(asyncio.TimeoutError):
            await run_cli_command(["python", "-c", "import time; time.sleep(10)"], timeout=0.1)


class TestCLIAdapter:
    """Tests for CLIAdapter class."""

    def test_adapter_creation(self):
        """Test creating a CLI adapter."""
        adapter = CLIAdapter("echo")
        assert adapter.cli_name == "echo"

    def test_is_available_true(self):
        """Test that available CLI returns True."""
        adapter = CLIAdapter("echo")
        assert adapter.is_available() is True

    def test_is_available_false(self):
        """Test that missing CLI returns False."""
        adapter = CLIAdapter("definitely_missing_12345")
        assert adapter.is_available() is False

    def test_is_available_caches_result(self):
        """Test that availability is cached."""
        adapter = CLIAdapter("echo")
        first = adapter.is_available()
        second = adapter.is_available()
        assert first == second
        assert adapter._available is not None

    @pytest.mark.asyncio
    async def test_adapter_run(self):
        """Test running command through adapter."""
        adapter = CLIAdapter("echo")
        stdout, stderr = await adapter.run(["hello"])
        assert stdout == "hello"

    @pytest.mark.asyncio
    async def test_adapter_run_not_available(self):
        """Test that unavailable adapter raises."""
        adapter = CLIAdapter("definitely_missing_12345")
        with pytest.raises(CLINotFoundError):
            await adapter.run(["arg"])


class TestErrorMessages:
    """Tests for error message quality."""

    @pytest.mark.asyncio
    async def test_error_includes_command(self):
        """Test that error includes the command that failed."""
        with pytest.raises(CLIError) as exc_info:
            await run_cli_command(["python", "-c", "import sys; sys.exit(1)"])
        error_str = str(exc_info.value)
        assert "python" in error_str
        assert "exit code 1" in error_str

    @pytest.mark.asyncio
    async def test_error_includes_stderr(self):
        """Test that error includes stderr content."""
        with pytest.raises(CLIError) as exc_info:
            await run_cli_command(
                ["python", "-c", "import sys; print('error message', file=sys.stderr); sys.exit(1)"]
            )
        assert "error message" in str(exc_info.value)


class TestModelParsingIntegration:
    """Tests for CLIAdapter model parsing with Pydantic."""

    @pytest.mark.asyncio
    async def test_fetch_json_parses_echo_output(self):
        """Test that fetch_json parses echo JSON output."""
        adapter = CLIAdapter("echo")
        result = await adapter.fetch_json(['{"test": 1}'])
        assert result == {"test": 1}

    @pytest.mark.asyncio
    async def test_fetch_json_empty_output_returns_empty_list(self):
        """Test that empty output returns empty list."""
        adapter = CLIAdapter("echo")
        result = await adapter.fetch_json([""])
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_and_parse_with_pydantic_model(self):
        """Test that fetch_and_parse validates into Pydantic models."""
        from pydantic import BaseModel

        class TestItem(BaseModel):
            id: int
            name: str

        adapter = CLIAdapter("echo")
        # echo '[{"id": 1, "name": "test"}]' | parse
        result = await adapter.fetch_and_parse(['[{"id": 1, "name": "test"}]'], TestItem)
        assert len(result) == 1
        assert isinstance(result[0], TestItem)
        assert result[0].id == 1
        assert result[0].name == "test"

    @pytest.mark.asyncio
    async def test_fetch_and_parse_invalid_data_raises_validation_error(self):
        """Test that invalid data raises Pydantic validation error."""
        from pydantic import BaseModel
        from pydantic import ValidationError

        class TestItem(BaseModel):
            id: int
            name: str

        adapter = CLIAdapter("echo")
        # Missing 'name' field should raise ValidationError
        with pytest.raises(ValidationError):
            await adapter.fetch_and_parse(['[{"id": 1}]'], TestItem)

    @pytest.mark.asyncio
    async def test_fetch_and_parse_single_object(self):
        """Test that single object is wrapped in list."""
        from pydantic import BaseModel

        class TestItem(BaseModel):
            id: int

        adapter = CLIAdapter("echo")
        # Single object (not in array)
        result = await adapter.fetch_and_parse(['{"id": 42}'], TestItem)
        assert len(result) == 1
        assert result[0].id == 42

    @pytest.mark.asyncio
    async def test_fetch_and_parse_with_real_models(self):
        """Test integration with actual monokl models."""
        from monokl.models import MergeRequest

        adapter = CLIAdapter("echo")
        # Simulate a GitLab MR JSON response
        mr_json = """[{
            "iid": 42,
            "title": "Test MR",
            "state": "opened",
            "author": {"name": "Test User", "username": "testuser"},
            "web_url": "https://gitlab.com/test/project/-/merge_requests/42",
            "source_branch": "feature-branch",
            "target_branch": "main",
            "created_at": "2024-01-15T10:30:00Z",
            "draft": false
        }]"""

        result = await adapter.fetch_and_parse([mr_json], MergeRequest)
        assert len(result) == 1
        assert isinstance(result[0], MergeRequest)
        assert result[0].iid == 42
        assert result[0].title == "Test MR"
        assert result[0].state == "opened"
        assert result[0].display_key() == "!42"
