"""Integration tests for monocle.

These tests verify the full data flow from sources → WorkStore → UI
using mocked databases and data sources.
"""

import pytest


# Register custom markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "integration_smoke: fast deterministic integration tests")
    config.addinivalue_line("markers", "integration_full: broader integration scenario tests")
