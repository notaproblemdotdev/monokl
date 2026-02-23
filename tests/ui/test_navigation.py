"""Keyboard/navigation tests for dashboard sections."""

from __future__ import annotations

from typing import cast

import pytest

from monocle.ui.main_screen import MainScreen
from monocle.ui.sections import CodeReviewSubSection
from tests.support.factories import make_code_review
from tests.support.factories import make_jira_item

pytestmark = pytest.mark.asyncio


async def test_tab_switches_between_sections(app_with_stub_store) -> None:
    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.2)
        screen = cast("MainScreen", pilot.app.screen)

        assert screen.active_section == "mr"
        assert screen.active_mr_subsection == "assigned"

        await pilot.press("tab")
        assert screen.active_section == "mr"
        assert screen.active_mr_subsection == "opened"

        await pilot.press("tab")
        assert screen.active_section == "work"


async def test_jk_navigation_in_code_review_section(
    app_with_stub_store, stub_gitlab_source
) -> None:
    stub_gitlab_source.assigned = [
        make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊"),
        make_code_review(idx=2, adapter_type="gitlab", adapter_icon="🦊"),
        make_code_review(idx=3, adapter_type="gitlab", adapter_icon="🦊"),
    ]

    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.6)
        screen = cast("MainScreen", pilot.app.screen)
        section = screen.code_review_section.assigned_to_me_section
        assert section.state == "data"

        initial = section._data_table.cursor_row
        await pilot.press("j")
        down = section._data_table.cursor_row
        await pilot.press("k")
        up = section._data_table.cursor_row

        assert initial is not None
        assert down is not None
        assert up is not None


async def test_o_key_opens_selected_review(
    app_with_stub_store, stub_gitlab_source, monkeypatch
) -> None:
    expected = make_code_review(idx=42, adapter_type="gitlab", adapter_icon="🦊")
    stub_gitlab_source.assigned = [expected]

    opened: list[str] = []

    def mock_open(url: str) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr("webbrowser.open", mock_open)

    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.6)
        screen = cast("MainScreen", pilot.app.screen)
        screen.code_review_section.focus_section("assigned")
        await pilot.press("o")

    assert opened == [expected.url]


async def test_o_key_opens_selected_work_item(
    app_with_stub_store, stub_jira_source, monkeypatch
) -> None:
    item = make_jira_item(idx=5)
    stub_jira_source.items = [item]

    opened: list[str] = []

    def mock_open(url: str) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr("webbrowser.open", mock_open)

    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.6)
        await pilot.press("tab")
        await pilot.press("tab")
        screen = cast("MainScreen", pilot.app.screen)
        screen.piece_of_work_section.focus_table()
        await pilot.press("o")

    assert opened == [item.url]


async def test_section_helper_get_selected_url() -> None:
    section = CodeReviewSubSection()
    section.update_data([])
    assert section.get_selected_url() is None
