"""Tests for MainScreen behavior with stubbed sources."""

from __future__ import annotations

from typing import cast

import pytest

from monokl.ui.main_screen import MainScreen
from monokl.ui.sections import SectionState
from tests.support.factories import make_code_review
from tests.support.factories import make_jira_item

pytestmark = pytest.mark.asyncio


def _get_main_screen(app) -> MainScreen:
    for screen in app.screen_stack:
        if isinstance(screen, MainScreen):
            return screen
    raise AssertionError("MainScreen not found")


async def test_main_screen_renders_both_sections(app_with_stub_store) -> None:
    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.8)
        screen = _get_main_screen(pilot.app)
        assert screen.query_one("#mr-container") is not None
        assert screen.query_one("#work-container") is not None


async def test_loading_resolves_to_data_with_stub_data(
    app_with_stub_store,
    stub_gitlab_source,
    stub_jira_source,
) -> None:
    stub_gitlab_source.assigned = [
        make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊")
    ]
    stub_jira_source.items = [make_jira_item(idx=1)]

    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.6)
        screen = cast("MainScreen", pilot.app.screen)

        assert screen.code_review_section.assigned_to_me_section.state == SectionState.DATA
        assert screen.piece_of_work_section.state == SectionState.DATA


async def test_tab_switching_updates_active_section(app_with_stub_store) -> None:
    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.2)
        screen = cast("MainScreen", pilot.app.screen)

        assert screen.active_section == "mr"
        assert screen.active_mr_subsection == "assigned"

        await pilot.press("tab")
        assert screen.active_mr_subsection == "opened"

        await pilot.press("tab")
        assert screen.active_section == "work"


async def test_refresh_invokes_section_reload(
    app_with_stub_store,
    stub_gitlab_source,
) -> None:
    stub_gitlab_source.assigned = [
        make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊")
    ]

    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.6)
        screen = cast("MainScreen", pilot.app.screen)

        assert len(screen.code_review_section.assigned_to_me_section.code_reviews) == 1

        stub_gitlab_source.assigned = [
            make_code_review(idx=2, adapter_type="gitlab", adapter_icon="🦊")
        ]
        await pilot.press("r")
        await pilot.pause(0.6)

        reviews = screen.code_review_section.assigned_to_me_section.code_reviews
        assert len(reviews) == 1
        assert reviews[0].id == "gitlab-2"


async def test_source_failure_sets_error_state(app_with_stub_store, stub_gitlab_source) -> None:
    stub_gitlab_source.assigned_exception = Exception("boom")

    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.6)
        screen = cast("MainScreen", pilot.app.screen)
        section = screen.code_review_section.assigned_to_me_section

        assert section.state in {SectionState.EMPTY, SectionState.ERROR}
        assert "gitlab" in screen._source_errors
