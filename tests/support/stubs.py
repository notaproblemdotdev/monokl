"""Reusable stub sources for integration and UI tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from monokl.models import CodeReview
from monokl.models import PieceOfWork
from monokl.sources.base import CodeReviewSource
from monokl.sources.base import PieceOfWorkSource
from tests.support.factories import make_code_review
from tests.support.factories import make_jira_item
from tests.support.factories import make_todoist_item


class StubCodeReviewSource(CodeReviewSource):
    """Deterministic code-review source stub with configurable behavior."""

    def __init__(
        self,
        *,
        source_type: str,
        source_icon: str,
        assigned: list[CodeReview] | None = None,
        authored: list[CodeReview] | None = None,
        pending: list[CodeReview] | None = None,
        available: bool = True,
        authenticated: bool = True,
        fetch_delay: float = 0.0,
        assigned_exception: Exception | None = None,
        authored_exception: Exception | None = None,
        pending_exception: Exception | None = None,
    ):
        self._source_type = source_type
        self._source_icon = source_icon
        self.assigned = assigned or []
        self.authored = authored or []
        self.pending = pending or []
        self.available = available
        self.authenticated = authenticated
        self.fetch_delay = fetch_delay
        self.assigned_exception = assigned_exception
        self.authored_exception = authored_exception
        self.pending_exception = pending_exception

    @property
    def source_type(self) -> str:
        return self._source_type

    @property
    def source_icon(self) -> str:
        return self._source_icon

    async def is_available(self) -> bool:
        return self.available

    async def check_auth(self) -> bool:
        return self.authenticated

    async def _sleep_if_needed(self) -> None:
        if self.fetch_delay > 0:
            await asyncio.sleep(self.fetch_delay)

    async def fetch_assigned(self) -> list[CodeReview]:
        await self._sleep_if_needed()
        if self.assigned_exception is not None:
            raise self.assigned_exception
        return self.assigned

    async def fetch_authored(self) -> list[CodeReview]:
        await self._sleep_if_needed()
        if self.authored_exception is not None:
            raise self.authored_exception
        return self.authored

    async def fetch_pending_review(self) -> list[CodeReview]:
        await self._sleep_if_needed()
        if self.pending_exception is not None:
            raise self.pending_exception
        return self.pending


class StubPieceOfWorkSource(PieceOfWorkSource):
    """Deterministic work-item source stub with configurable behavior."""

    def __init__(
        self,
        *,
        source_type: str,
        source_icon: str,
        items: list[PieceOfWork] | None = None,
        available: bool = True,
        authenticated: bool = True,
        fetch_delay: float = 0.0,
        items_exception: Exception | None = None,
    ):
        self._source_type = source_type
        self._source_icon = source_icon
        self.items = items or []
        self.available = available
        self.authenticated = authenticated
        self.fetch_delay = fetch_delay
        self.items_exception = items_exception

    @property
    def source_type(self) -> str:
        return self._source_type

    @property
    def source_icon(self) -> str:
        return self._source_icon

    async def is_available(self) -> bool:
        return self.available

    async def check_auth(self) -> bool:
        return self.authenticated

    async def fetch_items(self) -> list[PieceOfWork]:
        if self.fetch_delay > 0:
            await asyncio.sleep(self.fetch_delay)
        if self.items_exception is not None:
            raise self.items_exception
        return self.items


@dataclass(slots=True)
class StubScenario:
    """Container for source stubs used by test scenarios."""

    gitlab: StubCodeReviewSource
    github: StubCodeReviewSource
    jira: StubPieceOfWorkSource
    todoist: StubPieceOfWorkSource


class StubScenarioBuilder:
    """Predefined scenario builder for integration tests."""

    @staticmethod
    def success() -> StubScenario:
        return StubScenario(
            gitlab=StubCodeReviewSource(
                source_type="gitlab",
                source_icon="🦊",
                assigned=[make_code_review(idx=1, adapter_type="gitlab", adapter_icon="🦊")],
                authored=[make_code_review(idx=2, adapter_type="gitlab", adapter_icon="🦊")],
            ),
            github=StubCodeReviewSource(
                source_type="github",
                source_icon="🐙",
                assigned=[make_code_review(idx=3, adapter_type="github", adapter_icon="🐙")],
            ),
            jira=StubPieceOfWorkSource(
                source_type="jira",
                source_icon="🔴",
                items=[make_jira_item(idx=1)],
            ),
            todoist=StubPieceOfWorkSource(
                source_type="todoist",
                source_icon="📝",
                items=[make_todoist_item(idx=1)],
            ),
        )

    @staticmethod
    def partial_failure() -> StubScenario:
        scenario = StubScenarioBuilder.success()
        scenario.gitlab.assigned_exception = TimeoutError("GitLab timeout")
        return scenario

    @staticmethod
    def auth_failure() -> StubScenario:
        scenario = StubScenarioBuilder.success()
        scenario.gitlab.authenticated = False
        scenario.github.authenticated = False
        return scenario

    @staticmethod
    def unavailable() -> StubScenario:
        scenario = StubScenarioBuilder.success()
        scenario.gitlab.available = False
        scenario.jira.available = False
        return scenario
