"""Tests for section widgets using current CodeReview/PieceOfWork models."""

from __future__ import annotations

from textual.app import App
from textual.app import ComposeResult

import pytest

from monocle.ui.sections import CodeReviewSection
from monocle.ui.sections import CodeReviewSubSection
from monocle.ui.sections import PieceOfWorkSection
from monocle.ui.sections import SectionState
from tests.support.factories import make_code_review
from tests.support.factories import make_jira_item


class SectionHarness(App[None]):
    """Tiny app harness for mounting a single section widget."""

    def __init__(self, section) -> None:
        super().__init__()
        self.section = section

    def compose(self) -> ComposeResult:
        yield self.section


async def test_code_review_subsection_renders_table() -> None:
    section = CodeReviewSubSection()
    app = SectionHarness(section)

    async with app.run_test() as pilot:
        await pilot.pause()
        table = section.query_one("#data-table")
        assert table is not None


async def test_code_review_subsection_updates_data() -> None:
    section = CodeReviewSubSection()
    app = SectionHarness(section)

    reviews = [
        make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊"),
        make_code_review(idx=2, adapter_type="github", adapter_icon="🐙"),
    ]

    async with app.run_test() as pilot:
        await pilot.pause()
        section.update_data(reviews)
        await pilot.pause()

        assert section.state == SectionState.DATA
        assert section._item_count == 2


async def test_code_review_subsection_state_transitions() -> None:
    section = CodeReviewSubSection()
    app = SectionHarness(section)

    async with app.run_test() as pilot:
        await pilot.pause()
        section.show_loading("Loading")
        await pilot.pause()
        assert section.state == SectionState.LOADING

        section.set_error("boom")
        await pilot.pause()
        assert section.state == SectionState.ERROR

        section.update_data([])
        await pilot.pause()
        assert section.state == SectionState.EMPTY


async def test_code_review_subsection_truncates_long_title() -> None:
    section = CodeReviewSubSection()
    long_title = "A" * 120
    truncated = section._truncate_title(long_title)

    assert len(truncated) <= 40
    assert truncated.endswith("...")


async def test_code_review_section_renders_two_subsections() -> None:
    section = CodeReviewSection()
    app = SectionHarness(section)

    async with app.run_test() as pilot:
        await pilot.pause()
        opened = app.query_one("#cr-opened-by-me")
        assigned = app.query_one("#cr-assigned-to-me")

        assert opened is not None
        assert assigned is not None


async def test_code_review_section_update_methods() -> None:
    section = CodeReviewSection()
    app = SectionHarness(section)

    assigned_reviews = [make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊")]
    opened_reviews = [make_code_review(idx=2, adapter_type="gitlab", adapter_icon="🦊")]

    async with app.run_test() as pilot:
        await pilot.pause()
        section.update_assigned_to_me(assigned_reviews)
        section.update_opened_by_me(opened_reviews)
        await pilot.pause()

        assert section.assigned_to_me_section.state == SectionState.DATA
        assert section.opened_by_me_section.state == SectionState.DATA


async def test_piece_of_work_section_updates_data() -> None:
    section = PieceOfWorkSection()
    app = SectionHarness(section)

    items = [make_jira_item(idx=1), make_jira_item(idx=2)]

    async with app.run_test() as pilot:
        await pilot.pause()
        section.update_data(items)
        await pilot.pause()

        assert section.state == SectionState.DATA
        assert section._item_count == 2


async def test_piece_of_work_section_empty_state() -> None:
    section = PieceOfWorkSection()
    app = SectionHarness(section)

    async with app.run_test() as pilot:
        await pilot.pause()
        section.update_data([])
        await pilot.pause()

        assert section.state == SectionState.EMPTY


def test_jira_priority_mapping() -> None:
    item = make_jira_item(idx=1, priority="High")
    assert item.priority == 4


def test_code_review_section_active_lookup() -> None:
    section = CodeReviewSection()

    assert section.get_active_section("assigned") is section.assigned_to_me_section
    assert section.get_active_section("opened") is section.opened_by_me_section
    assert section.get_active_section("unknown") is None
