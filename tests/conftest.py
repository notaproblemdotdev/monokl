"""pytest fixtures and configuration."""

import pytest


@pytest.fixture
def event_loop_policy():
    """Return event loop policy for async tests."""
    import asyncio

    return asyncio.get_event_loop_policy()
