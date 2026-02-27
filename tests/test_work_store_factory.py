"""Tests for work store source registration."""

from __future__ import annotations

from monokl.ui.work_store_factory import create_work_store


class _DummyConfig:
    cache_ttl = 300
    gitlab_group = None
    jira_base_url = None
    todoist_token = None
    todoist_projects: tuple[str, ...] = ()
    todoist_show_completed = False
    todoist_show_completed_for_last = None
    azuredevops_token = None
    azuredevops_organizations: tuple[str, ...] = ()


def test_create_work_store_registers_default_sources() -> None:
    store = create_work_store(_DummyConfig())

    code_review_sources = [s.source_type for s in store._registry.get_code_review_sources()]
    work_item_sources = [s.source_type for s in store._registry.get_piece_of_work_sources()]

    assert "gitlab" in code_review_sources
    assert "github" in code_review_sources
    assert "github" in work_item_sources
    assert "jira" in work_item_sources
