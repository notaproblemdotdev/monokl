"""UI package for monokl.

This package provides Textual-based widgets for the dashboard interface,
including section widgets for displaying merge requests and work items.
"""

from monokl.ui.app import MonoApp
from monokl.ui.sections import MergeRequestSection
from monokl.ui.sections import WorkItemSection
from monokl.ui.topbar import TopBar

__all__ = ["MergeRequestSection", "MonoApp", "TopBar", "WorkItemSection"]
