"""Factory for creating WorkStore instances with configured sources.

Provides a clean separation between WorkStore creation and UI code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from monocli import get_logger
from monocli.db import WorkStore

if TYPE_CHECKING:
    from monocli.config import Config
    from monocli.sources.registry import SourceRegistry

logger = get_logger(__name__)


def create_work_store(config: Config) -> WorkStore:
    """Create a WorkStore instance with all configured sources.

    This factory function initializes the source registry with all
    available sources (GitLab, GitHub, Jira, Todoist) based on the
    provided configuration.

    Args:
        config: Application configuration.

    Returns:
        Configured WorkStore instance ready for data fetching.

    Example:
        from monocli.config import get_config
        from monocli.ui.work_store_factory import create_work_store

        config = get_config()
        store = create_work_store(config)
        result = await store.get_code_reviews("assigned")
    """
    from monocli.sources import SourceRegistry

    registry = SourceRegistry()

    _register_code_review_sources(registry, config)
    _register_work_sources(registry, config)

    return WorkStore(
        source_registry=registry,
        code_review_ttl=config.cache_ttl,
        work_item_ttl=config.cache_ttl * 2,  # Work items change less frequently
    )


def _register_code_review_sources(registry: SourceRegistry, config: Config) -> None:
    """Register all configured code review sources."""
    _register_gitlab(registry, config)
    _register_github(registry)


def _register_work_sources(registry: SourceRegistry, config: Config) -> None:
    """Register all configured work item sources."""
    _register_jira(registry, config)
    _register_todoist(registry, config)


def _register_gitlab(registry: SourceRegistry, config: Config) -> None:
    """Register GitLab source if configured."""
    from monocli.config import ConfigError
    from monocli.sources import GitLabSource

    try:
        group = config.require_gitlab_group()
        gitlab_source = GitLabSource(group=group)
        registry.register_code_review_source(gitlab_source)
        logger.debug("Registered GitLab source")
    except ConfigError:
        logger.debug("GitLab not configured, skipping")
    except Exception as e:
        logger.warning("Failed to initialize GitLab source", error=str(e))


def _register_github(registry: SourceRegistry) -> None:
    """Register GitHub source."""
    from monocli.sources import GitHubSource

    try:
        github_source = GitHubSource()
        registry.register_code_review_source(github_source)
        logger.debug("Registered GitHub source")
    except Exception as e:
        logger.warning("Failed to initialize GitHub source", error=str(e))


def _register_jira(registry: SourceRegistry, config: Config) -> None:
    """Register Jira source if configured."""
    from monocli.config import ConfigError
    from monocli.sources import JiraSource

    try:
        base_url = config.require_jira_base_url()
        jira_source = JiraSource(base_url=base_url)
        registry.register_piece_of_work_source(jira_source)
        logger.debug("Registered Jira source")
    except ConfigError:
        logger.debug("Jira not configured, skipping")
    except Exception as e:
        logger.warning("Failed to initialize Jira source", error=str(e))


def _register_todoist(registry: SourceRegistry, config: Config) -> None:
    """Register Todoist source if token is available."""
    from monocli.sources import TodoistSource

    if not config.todoist_token:
        logger.debug("Todoist not configured, skipping")
        return

    try:
        todoist_source = TodoistSource(
            token=config.todoist_token,
            project_names=config.todoist_projects,
            show_completed=config.todoist_show_completed,
            show_completed_for_last=config.todoist_show_completed_for_last,
        )
        registry.register_piece_of_work_source(todoist_source)
        logger.debug("Registered Todoist source")
    except Exception as e:
        logger.warning("Failed to initialize Todoist source", error=str(e))
