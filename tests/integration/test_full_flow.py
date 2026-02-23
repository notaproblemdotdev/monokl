"""Integration tests covering end-to-end happy paths."""

from __future__ import annotations

import asyncio
from typing import cast

import pytest

from monocle.ui.main_screen import MainScreen
from monocle.ui.sections import SectionState
from tests.support.factories import make_code_review
from tests.support.factories import make_jira_item
from tests.support.factories import make_todoist_item

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.integration_smoke
async def test_fetch_and_display_all_sources(
    app_with_mocked_store,
    mock_gitlab_source,
    mock_github_source,
    mock_jira_source,
    mock_todoist_source,
) -> None:
    """App should render data from all configured source stubs."""
    mock_gitlab_source.assigned = [
        make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊")
    ]
    mock_github_source.assigned = [
        make_code_review(idx=2, adapter_type="github", adapter_icon="🐙")
    ]
    mock_jira_source.items = [make_jira_item(idx=1)]
    mock_todoist_source.items = [make_todoist_item(idx=1)]

    async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        screen = cast("MainScreen", pilot.app.screen)

        assigned_section = screen.code_review_section.assigned_to_me_section
        work_section = screen.piece_of_work_section

        assert assigned_section.state == SectionState.DATA
        assert work_section.state == SectionState.DATA
        assert len(assigned_section.code_reviews) == 2
        assert len(work_section.work_items) == 2


@pytest.mark.integration_smoke
async def test_section_navigation(app_with_mocked_store) -> None:
    """Tab should cycle assigned -> opened -> work -> assigned."""
    async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)
        screen = cast("MainScreen", pilot.app.screen)

        assert screen.active_section == "mr"
        assert screen.active_mr_subsection == "assigned"

        await pilot.press("tab")
        assert screen.active_section == "mr"
        assert screen.active_mr_subsection == "opened"

        await pilot.press("tab")
        assert screen.active_section == "work"

        await pilot.press("tab")
        assert screen.active_section == "mr"
        assert screen.active_mr_subsection == "assigned"


@pytest.mark.integration_full
async def test_cache_refresh_cycle(mock_work_store, mock_gitlab_source) -> None:
    """WorkStore should return stale cache when source fails, then recover on refresh."""
    mock_gitlab_source.assigned = [
        make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊")
    ]

    first = await mock_work_store.get_code_reviews("assigned", force_refresh=True)
    assert first.fresh is True
    assert len(first.data) == 1

    mock_gitlab_source.assigned_exception = TimeoutError("temporary failure")
    stale = await mock_work_store.get_code_reviews("assigned")
    assert stale.fresh is False
    assert len(stale.data) == 1

    mock_gitlab_source.assigned_exception = None
    mock_gitlab_source.assigned = [
        make_code_review(idx=2, adapter_type="gitlab", adapter_icon="🦊")
    ]
    refreshed = await mock_work_store.get_code_reviews("assigned", force_refresh=True)
    assert refreshed.fresh is True
    assert [item.id for item in refreshed.data] == ["gitlab-2"]


@pytest.mark.integration_full
async def test_concurrent_fetch_behavior(
    mock_work_store,
    mock_gitlab_source,
    mock_jira_source,
) -> None:
    """Code reviews and work items should fetch concurrently."""
    mock_gitlab_source.assigned = [
        make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊")
    ]
    mock_jira_source.items = [make_jira_item(idx=1)]
    mock_gitlab_source.fetch_delay = 0.15
    mock_jira_source.fetch_delay = 0.15

    import time

    start = time.monotonic()
    cr_result, work_result = await asyncio.gather(
        mock_work_store.get_code_reviews("assigned", force_refresh=True),
        mock_work_store.get_work_items(force_refresh=True),
    )
    elapsed = time.monotonic() - start

    assert elapsed < 0.28
    assert len(cr_result.data) == 1
    assert len(work_result.data) == 1
