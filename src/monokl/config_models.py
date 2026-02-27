"""Pydantic models for monokl configuration.

Provides validated configuration models with defaults and type safety.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class Timeframe(str, Enum):
    """Valid timeframe values for todoist.show_completed_for_last."""

    H24 = "24h"
    H48 = "48h"
    H72 = "72h"
    D7 = "7days"


class GitLabConfig(BaseModel):
    """GitLab configuration."""

    model_config = ConfigDict(extra="forbid")

    group: str | None = None
    base_url: str | None = None


class JiraConfig(BaseModel):
    """Jira configuration."""

    model_config = ConfigDict(extra="forbid")

    project: str | None = None
    base_url: str | None = None


class TodoistConfig(BaseModel):
    """Todoist configuration."""

    model_config = ConfigDict(extra="forbid")

    token: str | None = None
    projects: list[str] = Field(default_factory=list)
    show_completed: bool = False
    show_completed_for_last: Timeframe | None = None


class AzureDevOpsOrgProject(BaseModel):
    """Single Azure DevOps organization/project configuration."""

    model_config = ConfigDict(extra="forbid")

    organization: str
    project: str


class AzureDevOpsConfig(BaseModel):
    """Azure DevOps configuration."""

    model_config = ConfigDict(extra="forbid")

    organizations: list[AzureDevOpsOrgProject] = Field(default_factory=list)


class CacheConfig(BaseModel):
    """Cache/Database configuration."""

    model_config = ConfigDict(extra="forbid")

    db_path: str | None = None
    ttl_seconds: int = 300
    cleanup_days: int = 30


class DevConfig(BaseModel):
    """Development settings."""

    model_config = ConfigDict(extra="forbid")

    show_logs_command: str = "tail -f {file}"


class UIConfig(BaseModel):
    """UI settings."""

    model_config = ConfigDict(extra="forbid")

    preserve_sort_preference: bool = True


class FeaturesConfig(BaseModel):
    """Feature flags configuration."""

    model_config = ConfigDict(extra="forbid")

    experimental: bool = False


class AdapterTypeConfig(BaseModel):
    """Configuration for a specific adapter type."""

    model_config = ConfigDict(extra="allow")

    selected: str | None = None


class IntegrationAdapters(BaseModel):
    """Adapter configuration for an integration."""

    model_config = ConfigDict(extra="allow")

    cli: dict[str, Any] = Field(default_factory=dict)
    api: dict[str, Any] = Field(default_factory=dict)
    selected: Literal["cli", "api"] | None = None


class AdaptersConfig(BaseModel):
    """All adapter configurations."""

    model_config = ConfigDict(extra="allow")

    gitlab: IntegrationAdapters = Field(default_factory=IntegrationAdapters)
    jira: IntegrationAdapters = Field(default_factory=IntegrationAdapters)
    todoist: IntegrationAdapters = Field(default_factory=IntegrationAdapters)
    github: IntegrationAdapters = Field(default_factory=IntegrationAdapters)
    azuredevops: IntegrationAdapters = Field(default_factory=IntegrationAdapters)


class AppConfig(BaseModel):
    """Root application configuration."""

    model_config = ConfigDict(extra="forbid")

    gitlab: GitLabConfig = Field(default_factory=GitLabConfig)
    jira: JiraConfig = Field(default_factory=JiraConfig)
    todoist: TodoistConfig = Field(default_factory=TodoistConfig)
    azuredevops: AzureDevOpsConfig = Field(default_factory=AzureDevOpsConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    dev: DevConfig = Field(default_factory=DevConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    adapters: AdaptersConfig = Field(default_factory=AdaptersConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        """Create AppConfig from dictionary, handling missing keys gracefully."""
        return cls.model_validate(data)
