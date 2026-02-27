"""Todoist adapter for fetching tasks via REST API.

This module provides a standalone adapter for Todoist using the official
Python SDK. Unlike CLI-based adapters (GitLab, Jira), this adapter uses HTTP
API calls directly.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

from monokl.logging_config import get_logger

from ...models import DueInfo
from ...models import TodoistTask

logger = get_logger(__name__)

try:
    from todoist_api_python.api_async import TodoistAPIAsync
except ImportError:
    TodoistAPIAsync = None  # type: ignore[assignment,misc]


class TodoistAdapter:
    """Adapter for Todoist REST API using official Python SDK.

    Standalone adapter (not subclassing CLIAdapter) since Todoist uses
    HTTP API calls, not CLI subprocess execution.
    """

    def __init__(self, token: str) -> None:
        """Initialize the Todoist adapter.

        Args:
            token: Todoist API token

        Raises:
            ImportError: If todoist-api-python is not installed
        """
        if TodoistAPIAsync is None:
            raise ImportError(
                "todoist-api-python is required for Todoist integration. "
                "Install it with: uv add todoist-api-python"
            )
        self.token = token
        self._api: TodoistAPIAsync | None = None

    @property
    def api(self) -> TodoistAPIAsync:  # type: ignore[valid-type]
        """Lazy-init async SDK client.

        Returns:
            Initialized TodoistAPIAsync client
        """
        if self._api is None:
            self._api = TodoistAPIAsync(self.token)  # type: ignore[call-arg]
        return self._api

    async def check_auth(self) -> bool:
        """Verify token by fetching projects (lightweight check).

        Returns:
            True if token is valid, False otherwise
        """
        try:
            await self.api.get_projects()
            return True
        except Exception as e:
            logger.debug("Todoist auth check failed", exc_info=e)
            return False

    async def fetch_tasks(
        self,
        project_names: list[str] | None = None,
        show_completed: bool = False,
        show_completed_for_last: str | None = None,
    ) -> list[TodoistTask]:
        """Fetch tasks with optional filtering.

        Args:
            project_names: List of project names to filter (None = all projects)
            show_completed: Include completed tasks (all completed if no timeframe)
            show_completed_for_last: Narrow completed tasks to this window
                ("24h", "48h", "72h", "7days"). Only used when show_completed=True.

        Returns:
            List of TodoistTask models
        """
        # 1. Get all projects to build name-to-ID mapping
        try:
            projects_list: list[Any] = []
            projects_gen = await self.api.get_projects()
            async for page in projects_gen:
                # Page is a list of projects
                projects_list.extend(page)
        except Exception as e:
            logger.error("Failed to fetch Todoist projects", exc_info=e)
            return []

        project_id_to_name = {p.id: p.name for p in projects_list}

        # 2. Resolve project IDs if filtering by name
        target_project_ids: set[str] | None = None
        if project_names:
            target_project_ids = {
                pid for pid, pname in project_id_to_name.items() if pname in project_names
            }
            logger.info(
                "Filtering by projects",
                projects=project_names,
                resolved_ids=target_project_ids,
            )

        # 3. Fetch active tasks
        try:
            active_tasks: list[Any] = []
            tasks_gen = await self.api.get_tasks()
            async for page in tasks_gen:
                # Page is a list of tasks
                active_tasks.extend(page)
        except Exception as e:
            logger.error("Failed to fetch Todoist tasks", exc_info=e)
            return []

        # 4. Optionally fetch completed tasks
        # NOTE: Completed tasks use a separate Sync API endpoint.
        # The SDK exposes this as get_completed_items(), NOT get_tasks(is_completed=True).
        completed_tasks: list[Any] = []
        if show_completed:
            try:
                # get_completed_items may not exist in all SDK versions
                # Use getattr to check if it's available
                get_completed = getattr(self.api, "get_completed_items", None)
                if callable(get_completed):
                    completed_result = await get_completed()  # type: ignore[misc]
                    if isinstance(completed_result, list):
                        completed_tasks = completed_result
                    else:
                        # It's an async generator, iterate over it
                        async for task in completed_result:  # type: ignore[assignment]
                            completed_tasks.append(task)
            except Exception as e:
                logger.warning(
                    "Failed to fetch completed Todoist tasks",
                    exc_info=e,
                )

        # 5. Convert to models with filtering
        all_tasks = active_tasks + completed_tasks
        tasks = []
        for t in all_tasks:
            # Filter by project if specified
            if target_project_ids and t.project_id not in target_project_ids:
                continue

            # Filter completed by time window if specified
            if (
                t.is_completed
                and show_completed_for_last
                and not self._is_within_timeframe(
                    t.completed_at,
                    show_completed_for_last,
                )
            ):
                continue

            tasks.append(self._task_to_model(t, project_id_to_name))

        logger.info("Fetched Todoist tasks", count=len(tasks))
        return tasks

    def _task_to_model(
        self,
        task: Any,  # Task from SDK
        project_id_to_name: dict[str, str],
    ) -> TodoistTask:
        """Convert SDK Task to TodoistTask model.

        Args:
            task: SDK Task object
            project_id_to_name: Mapping from project ID to name

        Returns:
            TodoistTask model
        """
        due_info: DueInfo | None = None
        if task.due:  # type: ignore[attr-defined]
            # Convert date object to string if needed
            due_date = task.due.date
            if hasattr(due_date, "isoformat"):
                due_date = due_date.isoformat()
            due_info = DueInfo(
                date=due_date,
                is_recurring=task.due.is_recurring,  # type: ignore[attr-defined]
                datetime=getattr(task.due, "datetime", None),
                string=getattr(task.due, "string", None),
                timezone=getattr(task.due, "timezone", None),
            )

        return TodoistTask(
            id=task.id,  # type: ignore[attr-defined]
            content=task.content,  # type: ignore[attr-defined]
            priority=task.priority,  # type: ignore[attr-defined]
            due=due_info,
            project_id=task.project_id,  # type: ignore[attr-defined]
            project_name=project_id_to_name.get(task.project_id, "Unknown"),  # type: ignore[attr-defined]
            url=str(task.url),  # type: ignore[attr-defined]
            created_at=str(task.created_at) if task.created_at else None,  # type: ignore[attr-defined]
            is_completed=task.is_completed,  # type: ignore[attr-defined]
            completed_at=str(task.completed_at) if task.completed_at else None,  # type: ignore[attr-defined]
        )

    def _is_within_timeframe(
        self,
        completed_at: str | None,
        timeframe: str,
    ) -> bool:
        """Check if completed datetime is within specified timeframe.

        Args:
            completed_at: ISO datetime string
            timeframe: One of "24h", "48h", "72h", "7days"

        Returns:
            True if within timeframe
        """
        if not completed_at:
            return False

        hours_map = {"24h": 24, "48h": 48, "72h": 72, "7days": 168}
        hours = hours_map.get(timeframe, 0)

        if hours == 0:
            return False

        try:
            dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            cutoff = datetime.now(UTC) - timedelta(hours=hours)
            return dt >= cutoff
        except (ValueError, TypeError):
            logger.warning(
                "Failed to parse completed_at",
                completed_at=completed_at,
            )
            return False
