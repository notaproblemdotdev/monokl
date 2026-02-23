"""Snapshot tests for key dashboard states."""

from __future__ import annotations

import pytest

from monocle.ui.main_screen import MainScreen
from monocle.ui.app import MonoApp
from tests.support.factories import make_code_review
from tests.support.factories import make_jira_item

pytestmark = [
    pytest.mark.integration,
    pytest.mark.integration_full,
    pytest.mark.asyncio,
    pytest.mark.snapshot,
]


def _get_main_screen(app: MonoApp) -> MainScreen:
    """Find MainScreen on the app's stack."""
    for screen in app.screen_stack:
        if isinstance(screen, MainScreen):
            return screen
    raise AssertionError("MainScreen not found in screen stack")


async def test_code_review_section_populated(
    monkeypatch: pytest.MonkeyPatch, mock_work_store, mock_gitlab_source, snapshot
) -> None:
    """Snapshot for populated code review section."""
    mock_gitlab_source.assigned = [
        make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊", title="Fix auth"),
        make_code_review(idx=2, adapter_type="gitlab", adapter_icon="🦊", title="Improve docs"),
    ]

    app = MonoApp()

    def mock_create_store(config):
        return mock_work_store

    monkeypatch.setattr("monocle.ui.work_store_factory.create_work_store", mock_create_store)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.8)
        screen = _get_main_screen(pilot.app)
        mr_container = screen.query_one("#mr-container")
        assert snapshot == mr_container


async def test_piece_of_work_section_populated(
    monkeypatch: pytest.MonkeyPatch, mock_work_store, mock_jira_source, snapshot
) -> None:
    """Snapshot for populated work section."""
    mock_jira_source.items = [make_jira_item(idx=1)]

    app = MonoApp()

    def mock_create_store(config):
        return mock_work_store

    monkeypatch.setattr("monocle.ui.work_store_factory.create_work_store", mock_create_store)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.8)
        screen = _get_main_screen(pilot.app)
        work_container = screen.query_one("#work-container")
        assert snapshot == work_container


async def test_error_state_visual(
    monkeypatch: pytest.MonkeyPatch, mock_work_store, mock_gitlab_source, snapshot
) -> None:
    """Snapshot for error state rendering."""
    mock_gitlab_source.assigned_exception = Exception("Connection failed")

    app = MonoApp()

    def mock_create_store(config):
        return mock_work_store

    monkeypatch.setattr("monocle.ui.work_store_factory.create_work_store", mock_create_store)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.8)
        screen = _get_main_screen(pilot.app)
        mr_container = screen.query_one("#mr-container")
        assert snapshot == mr_container
