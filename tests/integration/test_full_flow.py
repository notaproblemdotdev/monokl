"""Full flow integration tests.

Tests the complete data flow from sources → WorkStore → UI.
Includes fetching, caching, navigation, and interaction.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

from monocli.db.work_store import FetchResult
from monocli.models import CodeReview, JiraPieceOfWork, TodoistPieceOfWork
from monocli.ui.main_screen import MainScreen
from monocli.ui.sections import SectionState

if TYPE_CHECKING:
    from monocli.db.work_store import WorkStore
    from monocli.sources.registry import SourceRegistry
    from monocli.ui.app import MonoApp


# Sample data for tests
SAMPLE_GITLAB_MR = CodeReview(
    id="gl-1",
    key="!42",
    title="Fix authentication bug",
    state="open",
    author="developer1",
    source_branch="feature/auth-fix",
    url="https://gitlab.com/org/project/-/merge_requests/42",
    created_at=datetime(2025, 2, 15, 10, 30, 0),
    draft=False,
    adapter_type="gitlab",
    adapter_icon="🦊",
)

SAMPLE_GITHUB_PR = CodeReview(
    id="gh-1",
    key="#123",
    title="Refactor database layer",
    state="open",
    author="contributor1",
    source_branch="refactor/db",
    url="https://github.com/org/repo/pull/123",
    created_at=datetime(2025, 2, 13, 16, 45, 0),
    draft=False,
    adapter_type="github",
    adapter_icon="🐙",
)

SAMPLE_JIRA_ISSUE = JiraPieceOfWork(
    key="PROJ-123",
    fields={
        "summary": "Implement user authentication",
        "status": {"name": "In Progress"},
        "priority": {"name": "High"},
        "assignee": {"displayName": "Test User"},
    },
    self="https://jira.example.com/rest/api/2/issue/12345",
)

SAMPLE_TODOIST_TASK = TodoistPieceOfWork(
    id="123456789",
    content="Review pull requests",
    priority=4,
    due={"date": "2025-02-17", "string": "tomorrow"},
    project_id="123",
    project_name="Work",
    url="https://todoist.com/showTask?id=123456789",
    is_completed=False,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestFullFlow:
    """End-to-end integration tests."""

    async def test_fetch_and_display_all_sources(
        self,
        app_with_mocked_store: MonoApp,
        mock_gitlab_source,
        mock_github_source,
        mock_jira_source,
        mock_todoist_source,
    ) -> None:
        """Test fetching data from all sources and displaying in UI."""
        # Set up data for sources
        mock_gitlab_source._assigned = [SAMPLE_GITLAB_MR]
        mock_github_source._assigned = [SAMPLE_GITHUB_PR]
        mock_jira_source._items = [SAMPLE_JIRA_ISSUE]
        mock_todoist_source._items = [SAMPLE_TODOIST_TASK]

        async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            screen = cast(MainScreen, pilot.app.screen)
            await pilot.pause(0.5)

            assigned_section = screen.code_review_section.assigned_to_me_section
            work_section = screen.piece_of_work_section

            assert assigned_section.state == SectionState.DATA
            assert work_section.state == SectionState.DATA
            assert len(assigned_section.code_reviews) == 2
            assert len(work_section.work_items) == 2

    async def test_section_navigation(
        self,
        app_with_mocked_store: MonoApp,
    ) -> None:
        """Test Tab key navigation between sections."""
        async with app_with_mocked_store.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            screen = cast(MainScreen, pilot.app.screen)

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

    async def test_cache_refresh_cycle(
        self,
        mock_work_store: WorkStore,
        mock_gitlab_source,
    ) -> None:
        """Test cache behavior: stale cache → fresh data."""
        mock_gitlab_source._assigned = [SAMPLE_GITLAB_MR]

        result1 = await mock_work_store.get_code_reviews("assigned", force_refresh=True)
        assert result1.fresh is True
        assert len(result1.data) == 1

        result2 = await mock_work_store.get_code_reviews("assigned")
        assert result2.fresh is False

        result3 = await mock_work_store.get_code_reviews("assigned", force_refresh=True)
        assert result3.fresh is True

    async def test_multiple_sources_aggregation(
        self,
        mock_work_store: WorkStore,
        mock_gitlab_source,
        mock_github_source,
        mock_jira_source,
        mock_todoist_source,
    ) -> None:
        """Test that data from multiple sources is properly aggregated."""
        mock_gitlab_source._assigned = [SAMPLE_GITLAB_MR]
        mock_github_source._assigned = [SAMPLE_GITHUB_PR]
        mock_jira_source._items = [SAMPLE_JIRA_ISSUE]
        mock_todoist_source._items = [SAMPLE_TODOIST_TASK]

        result = await mock_work_store.get_code_reviews("assigned", force_refresh=True)
        gitlab_items = [r for r in result.data if r.adapter_type == "gitlab"]
        github_items = [r for r in result.data if r.adapter_type == "github"]

        assert len(gitlab_items) == 1
        assert len(github_items) == 1

        work_result = await mock_work_store.get_work_items(force_refresh=True)
        assert len(work_result.data) == 2

    async def test_concurrent_fetch_behavior(
        self,
        mock_work_store: WorkStore,
        mock_gitlab_source,
        mock_jira_source,
    ) -> None:
        """Test that fetches from multiple sources happen concurrently."""
        import time

        mock_gitlab_source._assigned = [SAMPLE_GITLAB_MR]
        mock_jira_source._items = [SAMPLE_JIRA_ISSUE]

        start = time.monotonic()
        results = await asyncio.gather(
            mock_work_store.get_code_reviews("assigned", force_refresh=True),
            mock_work_store.get_work_items(force_refresh=True),
        )
        elapsed = time.monotonic() - start

        assert elapsed < 1.0
        cr_result, work_result = results
        assert len(cr_result.data) == 1
        assert len(work_result.data) == 1
