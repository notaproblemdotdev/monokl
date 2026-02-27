"""Integration registry for monokl.

Defines metadata for all supported integrations including their
available adapters, CLI requirements, and factory functions.
"""

from __future__ import annotations

import typing as t
from dataclasses import dataclass
from dataclasses import field

if t.TYPE_CHECKING:
    from monokl.sources.base import SetupCapableSource


@dataclass(frozen=True, slots=True)
class IntegrationMeta:
    """Metadata for a supported integration."""

    id: str
    name: str
    icon: str
    description: str
    available_adapters: list[t.Literal["cli", "api"]]
    cli_name: str | None = None
    cli_install_url: str | None = None
    api_docs_url: str | None = None
    features: list[str] = field(default_factory=list)
    create_cli_adapter: t.Callable[[], SetupCapableSource] | None = None
    create_api_adapter: t.Callable[[], SetupCapableSource] | None = None


INTEGRATIONS: list[IntegrationMeta] = []

INTEGRATIONS_BY_ID: dict[str, IntegrationMeta] = {}


def _register_all_integrations() -> None:
    """Register all built-in integrations."""
    from monokl.sources.azuredevops import AzureDevOpsAPISetupSource
    from monokl.sources.github import GitHubCLISetupSource
    from monokl.sources.gitlab import GitLabCLISetupSource
    from monokl.sources.jira import JiraCLISetupSource
    from monokl.sources.todoist import TodoistAPISetupSource

    register_integration(
        IntegrationMeta(
            id="gitlab",
            name="GitLab",
            icon="🦊",
            description="Merge requests and issues from GitLab",
            available_adapters=["cli"],
            cli_name="glab",
            cli_install_url="https://gitlab.com/gitlab-org/cli",
            features=["merge_requests", "issues"],
            create_cli_adapter=GitLabCLISetupSource,
        )
    )

    register_integration(
        IntegrationMeta(
            id="github",
            name="GitHub",
            icon="🐙",
            description="Pull requests and issues from GitHub",
            available_adapters=["cli"],
            cli_name="gh",
            cli_install_url="https://cli.github.com",
            features=["pull_requests", "issues"],
            create_cli_adapter=GitHubCLISetupSource,
        )
    )

    register_integration(
        IntegrationMeta(
            id="jira",
            name="Jira",
            icon="🔴",
            description="Work items and issues from Jira",
            available_adapters=["cli"],
            cli_name="acli",
            cli_install_url="https://github.com/ankitpokhrel/jira-cli",
            features=["work_items", "issues"],
            create_cli_adapter=JiraCLISetupSource,
        )
    )

    register_integration(
        IntegrationMeta(
            id="todoist",
            name="Todoist",
            icon="📝",
            description="Tasks from Todoist",
            available_adapters=["api"],
            api_docs_url="https://developer.todoist.com/rest/v2",
            features=["tasks"],
            create_api_adapter=TodoistAPISetupSource,
        )
    )

    register_integration(
        IntegrationMeta(
            id="azuredevops",
            name="Azure DevOps",
            icon="🔷",
            description="Pull requests and work items from Azure DevOps",
            available_adapters=["api"],
            api_docs_url="https://learn.microsoft.com/en-us/rest/api/azure/devops",
            features=["pull_requests", "work_items"],
            create_api_adapter=AzureDevOpsAPISetupSource,
        )
    )


def register_integration(integration: IntegrationMeta) -> None:
    """Register an integration."""
    INTEGRATIONS.append(integration)
    INTEGRATIONS_BY_ID[integration.id] = integration


def get_integration(integration_id: str) -> IntegrationMeta | None:
    """Get integration by ID."""
    return INTEGRATIONS_BY_ID.get(integration_id)


def get_all_integrations() -> list[IntegrationMeta]:
    """Get all registered integrations."""
    return INTEGRATIONS.copy()


_register_all_integrations()
