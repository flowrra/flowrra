"""Service for schedule management operations."""

from typing import Any, Dict, List, Optional

from flowrra.management import FlowrraManager


class ScheduleService:
    """Service for managing schedules via the UI.

    Provides schedule CRUD operations:
    - List schedules
    - Get schedule details
    - Create schedules
    - Enable/disable schedules
    - Delete schedules

    This service wraps FlowrraManager schedule operations and
    provides a consistent API for UI adapters.
    """

    def __init__(self, manager: FlowrraManager):
        """Initialize schedule service.

        Args:
            manager: FlowrraManager instance for schedule operations
        """
        self.manager = manager

    async def list_schedules(
        self, enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """List schedules.

        Args:
            enabled_only: If True, only return enabled schedules

        Returns:
            List of schedules
        """
        return await self.manager.list_schedules(enabled_only=enabled_only)

    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get specific schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Schedule details or None
        """
        return await self.manager.get_schedule(schedule_id)

    async def create_schedule_cron(
        self,
        task_name: str,
        cron: str,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        enabled: bool = True,
        description: Optional[str] = None,
        priority: int = 0,
    ) -> Dict[str, str]:
        """Create cron schedule.

        Args:
            task_name: Task name
            cron: Cron expression
            args: Task arguments
            kwargs: Task keyword arguments
            enabled: Start enabled
            description: Optional description
            priority: Task priority

        Returns:
            Dictionary with schedule_id
        """
        schedule_id = await self.manager.create_schedule_cron(
            task_name=task_name,
            cron=cron,
            args=args,
            kwargs=kwargs or {},
            enabled=enabled,
            description=description,
            priority=priority,
        )
        return {"schedule_id": schedule_id}

    async def enable_schedule(self, schedule_id: str) -> Dict[str, str]:
        """Enable schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Success message
        """
        await self.manager.enable_schedule(schedule_id)
        return {"status": "enabled", "schedule_id": schedule_id}

    async def disable_schedule(self, schedule_id: str) -> Dict[str, str]:
        """Disable schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Success message
        """
        await self.manager.disable_schedule(schedule_id)
        return {"status": "disabled", "schedule_id": schedule_id}

    async def delete_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Delete schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Success status
        """
        deleted = await self.manager.delete_schedule(schedule_id)
        return {"deleted": deleted, "schedule_id": schedule_id}
