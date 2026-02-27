"""Data sources package for monokl.

Provides source protocols and implementations for fetching data from
various platforms (GitLab, GitHub, Jira, Todoist, Linear, etc.).
"""

from .azuredevops import AzureDevOpsSource
from .base import APIBaseAdapter
from .base import CLIBaseAdapter
from .base import CodeReviewSource
from .base import PieceOfWorkSource
from .base import Source
from .github import GitHubSource
from .gitlab import GitLabSource
from .jira import JiraSource
from .registry import SourceRegistry
from .todoist import TodoistSource

__all__ = [
    "APIBaseAdapter",
    "AzureDevOpsSource",
    "CLIBaseAdapter",
    "CodeReviewSource",
    "GitHubSource",
    "GitLabSource",
    "JiraSource",
    "PieceOfWorkSource",
    "Source",
    "Source",
    "SourceRegistry",
    "TodoistSource",
]
