"""UI package for monocli.

This package provides Textual-based widgets for the dashboard interface,
including section widgets for displaying merge requests and work items.
"""

from monocli.ui.app import MonoApp
from monocli.ui.sections import MergeRequestSection, WorkItemSection

__all__ = ["MergeRequestSection", "WorkItemSection", "MonoApp"]
