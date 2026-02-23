"""Integration tests for UI state transitions."""

from __future__ import annotations

from typing import cast

import pytest

from monocle.ui.main_screen import MainScreen
from monocle.ui.sections import SectionState
from tests.support.factories import make_code_review

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.integration_smoke
async def test_loading_to_data_transition(app_with_mocked_store, mock_gitlab_source) -> None:
    """Section should transition from loading to data with delayed source."""
    mock_gitlab_source.fetch_delay = 0.1
    mock_gitlab_source.assigned = [
        make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊")
    ]

    async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.05)
        screen = cast("MainScreen", pilot.app.screen)
        assigned = screen.code_review_section.assigned_to_me_section

        assert assigned.state in [SectionState.LOADING, SectionState.DATA]

        await pilot.pause(0.4)
        assert assigned.state == SectionState.DATA
        assert len(assigned.code_reviews) == 1


@pytest.mark.integration_smoke
async def test_empty_state_display(app_with_mocked_store, mock_gitlab_source) -> None:
    """Section should display EMPTY when no code reviews exist."""
    mock_gitlab_source.assigned = []
    mock_gitlab_source.authored = []

    async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        screen = cast("MainScreen", pilot.app.screen)
        assert screen.code_review_section.assigned_to_me_section.state == SectionState.EMPTY


@pytest.mark.integration_full
async def test_error_state_shows_message(app_with_mocked_store, mock_gitlab_source) -> None:
    """Failing source should be tracked while section remains non-data."""
    mock_gitlab_source.assigned_exception = Exception("Connection failed")

    async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        screen = cast("MainScreen", pilot.app.screen)
        section = screen.code_review_section.assigned_to_me_section

        assert section.state in {SectionState.EMPTY, SectionState.ERROR}
        assert "gitlab" in screen._source_errors


@pytest.mark.integration_full
async def test_refresh_from_error_to_data(app_with_mocked_store, mock_gitlab_source) -> None:
    """Manual refresh should recover section after transient failures."""
    call_count = 0

    async def flaky_fetch_assigned() -> list:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Temporary error")
        return [make_code_review(idx=2, adapter_type="gitlab", adapter_icon="🦊")]

    mock_gitlab_source.fetch_assigned = flaky_fetch_assigned

    async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        screen = cast("MainScreen", pilot.app.screen)
        section = screen.code_review_section.assigned_to_me_section

        assert section.state in {SectionState.EMPTY, SectionState.ERROR, SectionState.DATA}

        await pilot.press("r")
        await pilot.pause(0.5)

        assert section.state == SectionState.DATA
        assert len(section.code_reviews) == 1
        assert call_count >= 2
