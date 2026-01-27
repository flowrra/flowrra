"""Service for retrieving UI page data."""

import asyncio
from typing import Any, Dict, List, Optional

from flowrra.constants import TASK_STATUSES
from flowrra.management import FlowrraManager


class UIService:
    """Service for preparing data for UI pages.

    Handles data aggregation and transformation for:
    - Dashboard page
    - Tasks page
    - Schedules page

    This service acts as a bridge between FlowrraManager (raw data)
    and UI templates (formatted data).
    """

    def __init__(self, manager: FlowrraManager):
        """Initialize UI service.

        Args:
            manager: FlowrraManager instance for data access
        """
        self.manager = manager

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard page.

        Returns:
            Dictionary with dashboard data:
            {
                "stats": {...},
                "recent_failed_tasks": [...],
                "schedules": [...],
                "total_schedules": int
            }
        """
        stats, recent_failed, schedules = await asyncio.gather(
            self.manager.get_stats(),
            self.manager.list_failed_tasks(limit=10),
            self.manager.list_schedules(),
            return_exceptions=True
        )

        stats = {} if isinstance(stats, Exception) else stats
        recent_failed = [] if isinstance(recent_failed, Exception) else recent_failed
        schedules = [] if isinstance(schedules, Exception) else schedules

        return {
            "stats": stats,
            "recent_failed_tasks": recent_failed,
            "schedules": schedules[:5] if schedules else [],
            "total_schedules": len(schedules),
        }

    async def get_tasks_page_data(
        self, status: Optional[str] = None, limit: int = 200
    ) -> Dict[str, Any]:
        """Get data for tasks page.

        Args:
            status: Filter by status (pending/running/success/failed)
            limit: Maximum tasks to return (default: 200)

        Returns:
            Dictionary with tasks data
        """
        if status and status not in TASK_STATUSES:
            raise ValueError(f"Invalid task status: {status}")
        
        registered_tasks = await self.manager.list_registered_tasks()

        if status == "pending":
            tasks = await self._get_tasks_by_status("pending", limit=limit)
        elif status == "running":
            tasks = await self._get_tasks_by_status("running", limit=limit)
        elif status == "success":
            tasks = await self._get_tasks_by_status("success", limit=limit)
        elif status == "failed":
            tasks = await self._get_tasks_by_status("failed", limit=limit)
        else:
            results = await asyncio.gather(
                *[
                    self._get_tasks_by_status(status, limit // len(TASK_STATUSES))
                    for status in TASK_STATUSES
                ]
            )

            tasks = [task for group in results for task in group]

        return {
            "registered_tasks": registered_tasks,
            "tasks": tasks,
            "status_filter": status,
        }

    async def get_schedules_page_data(
        self, enabled_only: bool = False
    ) -> Dict[str, Any]:
        """Get data for schedules page.

        Args:
            enabled_only: If True, only return enabled schedules

        Returns:
            Dictionary with schedules data
        """
        schedules, scheduler_stats = await asyncio.gather(
            self.manager.list_schedules(enabled_only=enabled_only),
            self.manager.get_scheduler_stats()
        )

        return {
            "schedules": schedules,
            "scheduler_stats": scheduler_stats,
            "enabled_only": enabled_only,
        }

    async def _get_tasks_by_status(
        self, status: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Helper to get tasks by status name.

        Args:
            status: Status name (pending/running/success/failed)
            limit: Maximum tasks to return

        Returns:
            List of tasks
        """
        if status not in TASK_STATUSES:
            raise ValueError(f"Invalid task status: {status}")
        
        handlers = {
            "pending": self.manager.list_pending_tasks,
            "running": self.manager.list_running_tasks,
            "success": self.manager.list_completed_tasks,
            "failed": self.manager.list_failed_tasks,
        }

        handler = handlers.get(status)
        if not handler:
            return []

        return await handler(limit=limit)
