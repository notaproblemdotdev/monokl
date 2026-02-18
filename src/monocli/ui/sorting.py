"""Sorting utilities for table sections.

Provides sort methods, state management, and key extraction functions
for sorting work items and code reviews in DataTable widgets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from monocli.models import CodeReview
    from monocli.models import PieceOfWork


class SortMethod(str, Enum):
    """Available sort methods for tables."""

    PRIORITY = "priority"
    STATUS = "status"
    DATE = "date"
    NONE = "none"


@dataclass
class SortState:
    """Current sort state for a section."""

    method: SortMethod
    descending: bool = True

    def toggle_direction(self) -> SortState:
        """Return a new SortState with toggled direction."""
        return SortState(method=self.method, descending=not self.descending)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {"method": self.method.value, "descending": self.descending}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SortState:
        """Deserialize from dictionary."""
        method = SortMethod(data.get("method", SortMethod.NONE.value))
        descending = data.get("descending", True)
        return cls(method=method, descending=descending)

    @classmethod
    def default(cls) -> SortState:
        """Return default sort state (priority, descending)."""
        return cls(method=SortMethod.PRIORITY, descending=True)


SORT_INDICATOR_ASC = " ▲"
SORT_INDICATOR_DESC = " ▼"
SORT_INDICATOR_NONE = "  "


def get_sort_indicator(state: SortState | None) -> str:
    """Get the visual indicator for current sort state."""
    if state is None or state.method == SortMethod.NONE:
        return SORT_INDICATOR_NONE
    return SORT_INDICATOR_DESC if state.descending else SORT_INDICATOR_ASC


def get_work_item_sort_key(item: PieceOfWork, method: SortMethod) -> Any:
    """Extract sortable key from a PieceOfWork item.

    Args:
        item: The work item to extract key from.
        method: The sort method to use.

    Returns:
        A comparable value for sorting.
    """
    if method == SortMethod.PRIORITY:
        priority = item.priority
        if priority is None:
            return 0
        return priority
    if method == SortMethod.STATUS:
        status_order = {
            "IN PROGRESS": 1,
            "IN_PROGRESS": 1,
            "TODO": 2,
            "OPEN": 2,
            "BLOCKED": 3,
            "DONE": 4,
            "CLOSED": 4,
        }
        status_upper = item.display_status().upper()
        return status_order.get(status_upper, 5)
    if method == SortMethod.DATE:
        due = item.due_date
        if due is None:
            return ""
        return due
    return 0


def get_code_review_sort_key(review: CodeReview, method: SortMethod) -> Any:
    """Extract sortable key from a CodeReview item.

    Args:
        review: The code review to extract key from.
        method: The sort method to use.

    Returns:
        A comparable value for sorting.
    """
    if method == SortMethod.PRIORITY or method == SortMethod.STATUS:
        state_order = {"open": 1, "merged": 2, "closed": 3}
        return state_order.get(review.state.lower(), 4)
    if method == SortMethod.DATE:
        if review.created_at is None:
            return ""
        return review.created_at.isoformat()
    return 0
