from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from flowrra import Flowrra

from flowrra.management import FlowrraManager
from flowrra.ui.base.formatter import Formatter
from flowrra.ui.base.ui_service import UIService
from flowrra.ui.base.schedule_service import ScheduleService


class BaseUIAdapter(ABC):
    """Base adapter for framework-specific UI implementations.

    Framework-specific adapters (FastAPI, Flask, Django) inherit from
    this class and implement get_routes() to provide their routing logic.
    """

    def __init__(self, flowrra_app: "Flowrra"):
        """Initialize adapter with services.

        Args:
            flowrra_app: Flowrra application instance
        """
        self.flowrra = flowrra_app
        self.manager = FlowrraManager(flowrra_app)

        # Compose services
        self.ui_service = UIService(self.manager)
        self.schedule_service = ScheduleService(self.manager)
        self.formatter = Formatter

    @abstractmethod
    def get_routes(self) -> Any:
        """Return framework-specific routes.

        Returns:
            Framework-specific router/blueprint/urls object:
            - FastAPI: APIRouter
            - Flask: Blueprint
            - Django: List[URLPattern]
        """
        raise NotImplementedError

    # ========================================
    # File Paths
    # ========================================

    @property
    def templates_dir(self) -> Path:
        """Get templates directory path.

        Returns:
            Path to templates directory
        """
        # Go up one level from base/ to ui/, then to templates/
        return Path(__file__).parent.parent / "templates"

    @property
    def static_dir(self) -> Path:
        """Get static files directory path.

        Returns:
            Path to static files directory
        """
        # Go up one level from base/ to ui/, then to static/
        return Path(__file__).parent.parent / "static"

    # ========================================
    # UI Data Methods (Delegate to UIService)
    # ========================================

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard page.

        Returns:
            Dictionary with dashboard data
        """
        return await self.ui_service.get_dashboard_data()

    async def get_tasks_page_data(
        self, status: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        """Get data for tasks page.

        Args:
            status: Filter by status (pending/running/success/failed)
            limit: Maximum tasks to return

        Returns:
            Dictionary with tasks data
        """
        return await self.ui_service.get_tasks_page_data(status, limit)

    async def get_schedules_page_data(
        self, enabled_only: bool = False
    ) -> Dict[str, Any]:
        """Get data for schedules page.

        Args:
            enabled_only: If True, only return enabled schedules

        Returns:
            Dictionary with schedules data
        """
        return await self.ui_service.get_schedules_page_data(enabled_only)

    # ========================================
    # Formatting Utilities (Expose Formatter)
    # ========================================

    @staticmethod
    def format_datetime(dt: Any) -> str:
        """Format datetime for display.

        Args:
            dt: Datetime object or ISO string

        Returns:
            Formatted datetime string
        """
        return Formatter.format_datetime(dt)

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration (e.g., "2h 30m", "45s")
        """
        return Formatter.format_duration(seconds)

    @staticmethod
    def get_status_color(status: str) -> str:
        """Get color class for task status.

        Args:
            status: Task status string

        Returns:
            CSS color class name
        """
        return Formatter.get_status_color(status)

    # ========================================
    # API Endpoints (Standard Interface)
    # ========================================
    # These methods define the standard API interface
    # that all adapters should expose

    async def get_stats(self) -> Dict[str, Any]:
        """API endpoint: Get system statistics.

        Returns:
            System statistics dictionary
        """
        return await self.manager.get_stats()

    async def health_check(self) -> Dict[str, Any]:
        """API endpoint: Health check.

        Returns:
            Health status dictionary
        """
        return await self.manager.health_check()

    async def list_tasks(self) -> List[Dict[str, Any]]:
        """API endpoint: List registered tasks.

        Returns:
            List of registered tasks
        """
        return await self.manager.list_registered_tasks()

    async def get_task(self, task_name: str) -> Optional[Dict[str, Any]]:
        """API endpoint: Get specific task info.

        Args:
            task_name: Task name

        Returns:
            Task information or None
        """
        return await self.manager.get_task_info(task_name)

    async def list_schedules(
        self, enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """API endpoint: List schedules.

        Args:
            enabled_only: If True, only return enabled schedules

        Returns:
            List of schedules
        """
        return await self.schedule_service.list_schedules(enabled_only)

    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """API endpoint: Get specific schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Schedule details or None
        """
        return await self.schedule_service.get_schedule(schedule_id)

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
        """API endpoint: Create cron schedule.

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
        return await self.schedule_service.create_schedule_cron(
            task_name, cron, args, kwargs, enabled, description, priority
        )

    async def enable_schedule(self, schedule_id: str) -> Dict[str, str]:
        """API endpoint: Enable schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Success message
        """
        return await self.schedule_service.enable_schedule(schedule_id)

    async def disable_schedule(self, schedule_id: str) -> Dict[str, str]:
        """API endpoint: Disable schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Success message
        """
        return await self.schedule_service.disable_schedule(schedule_id)

    async def delete_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """API endpoint: Delete schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Success status
        """
        return await self.schedule_service.delete_schedule(schedule_id)
