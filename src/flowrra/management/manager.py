"""Core management API for Flowrra applications."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from flowrra.task import TaskStatus


class FlowrraManager:
    """Management interface for querying Flowrra application state.

    This class provides a framework-agnostic API for querying:
    - System statistics (executor status, task counts)
    - Registered tasks
    - Pending/completed tasks
    - Scheduler state and schedules

    Args:
        app: Flowrra application instance

    Example:
        manager = FlowrraManager(app)
        stats = await manager.get_stats()
        tasks = await manager.list_registered_tasks()
    """

    def __init__(self, app: "Flowrra"):  # noqa: F821
        """Initialize manager with Flowrra app."""
        self.app = app

    # ============================================
    # System Statistics
    # ============================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics.

        Returns:
            Dictionary with system state:
            {
                "app": {"running": bool},
                "executors": {
                    "io": {"running": bool, "workers": int} | None,
                    "cpu": {"running": bool, "workers": int} | None
                },
                "tasks": {
                    "registered": int,
                    "pending": int
                },
                "scheduler": {
                    "enabled": bool,
                    "schedules": int
                } | None
            }
        """
        stats = {
            "app": {"running": self.app.is_running},
            "executors": {
                "io": self._get_io_executor_stats(),
                "cpu": self._get_cpu_executor_stats(),
            },
            "tasks": {
                "registered": len(self.app.registry._tasks),
                "pending": await self._count_pending_tasks(),
            },
            "scheduler": await self._get_scheduler_stats_for_overview(),
        }

        return stats

    async def _get_scheduler_stats_for_overview(self) -> Optional[Dict[str, Any]]:
        """Get scheduler stats for overview (called by get_stats)."""
        if not self.app.scheduler:
            return None

        all_schedules = await self.app.scheduler.backend.list_all()

        return {
            "enabled": True,
            "running": self.app.scheduler.is_running,
            "total_schedules": len(all_schedules),
            "enabled_schedules": sum(1 for s in all_schedules if s.enabled),
        }

    def _get_io_executor_stats(self) -> Optional[Dict[str, Any]]:
        """Get IO executor statistics."""
        if not self.app._io_executor:
            return None

        executor = self.app._io_executor
        return {
            "running": executor.is_running,
            "workers": executor._io_workers,
        }

    def _get_cpu_executor_stats(self) -> Optional[Dict[str, Any]]:
        """Get CPU executor statistics."""
        if not self.app._cpu_executor:
            return None

        executor = self.app._cpu_executor
        return {
            "running": executor.is_running,
            "workers": executor._cpu_workers,
        }

    async def _count_pending_tasks(self) -> int:
        """Count pending tasks across all executors."""
        count = 0

        if self.app._io_executor and self.app._io_executor.is_running:
            try:
                if self.app._io_executor.is_broker():
                    count += await self.app._io_executor.broker.size()
                else:
                    count += self.app._io_executor.broker.qsize()
            except (AttributeError, NotImplementedError):
                pass

        if self.app._cpu_executor and self.app._cpu_executor.is_running:
            try:
                count += await self.app._cpu_executor.broker.size()
            except (AttributeError, Exception):
                pass

        return count

    # ============================================
    # Task Queries
    # ============================================

    async def list_registered_tasks(self) -> List[Dict[str, Any]]:
        """List all registered tasks.

        Returns:
            List of task information dictionaries:
            [
                {
                    "name": str,
                    "cpu_bound": bool,
                    "max_retries": int,
                    "retry_delay": float
                },
                ...
            ]
        """
        tasks = []

        for task_name, task_func in self.app.registry._tasks.items():
            task_info = {
                "name": task_name,
                "cpu_bound": getattr(task_func, "cpu_bound", False),
                "max_retries": getattr(task_func, "max_retries", 0),
                "retry_delay": getattr(task_func, "retry_delay", 0.0),
            }
            tasks.append(task_info)

        return tasks

    async def get_task_info(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific task.

        Args:
            task_name: Name of the task

        Returns:
            Task information dictionary or None if not found
        """
        task_func = self.app.registry.get(task_name)
        if not task_func:
            return None

        return {
            "name": task_name,
            "cpu_bound": getattr(task_func, "cpu_bound", False),
            "max_retries": getattr(task_func, "max_retries", 0),
            "retry_delay": getattr(task_func, "retry_delay", 0.0),
            "module": task_func.__module__,
            "qualname": task_func.__qualname__,
        }

    async def list_pending_tasks(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List pending tasks waiting for execution.

        Args:
            limit: Maximum number of tasks to return (None = no limit)

        Returns:
            List of pending task dictionaries, ordered by submission time (newest first)
        """
        backend = None
        if self.app._io_executor:
            backend = self.app._io_executor.results
        elif self.app._cpu_executor:
            backend = self.app._cpu_executor.results

        if backend is None:
            return []

        try:
            from flowrra.task import TaskStatus

            pending_results = await backend.list_by_status(
                status=TaskStatus.PENDING,
                limit=limit
            )

            return [
                {
                    "task_id": result.task_id,
                    "task_name": result.task_name,
                    "status": result.status.value,
                    "submitted_at": result.submitted_at,
                    "args": result.args,
                    "kwargs": result.kwargs,
                    "retries": result.retries,
                }
                for result in pending_results
            ]

        except NotImplementedError:
            import logging
            logger = logging.getLogger("flowrra")
            logger.warning(
                f"Backend {backend.__class__.__name__} doesn't support list_by_status()"
            )
            return []
        except Exception as e:
            import logging
            logger = logging.getLogger("flowrra")
            logger.error(f"Failed to list pending tasks: {e}")
            return []

    async def list_running_tasks(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List currently running tasks."""
        from flowrra.task import TaskStatus
        return await self._list_tasks_by_status(TaskStatus.RUNNING, limit)

    async def list_completed_tasks(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List successfully completed tasks."""
        from flowrra.task import TaskStatus
        return await self._list_tasks_by_status(TaskStatus.SUCCESS, limit)

    async def list_failed_tasks(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List failed tasks."""
        from flowrra.task import TaskStatus
        return await self._list_tasks_by_status(TaskStatus.FAILED, limit)

    async def _list_tasks_by_status(
        self,
        status: "TaskStatus",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Internal helper to list tasks by status."""
        backend = None
        if self.app._io_executor:
            backend = self.app._io_executor.results
        elif self.app._cpu_executor:
            backend = self.app._cpu_executor.results

        if backend is None:
            return []

        try:
            results = await backend.list_by_status(status=status, limit=limit)

            return [
                {
                    "task_id": result.task_id,
                    "task_name": result.task_name,
                    "status": result.status.value,
                    "submitted_at": result.submitted_at,
                    "started_at": result.started_at,
                    "finished_at": result.finished_at,
                    "args": result.args,
                    "kwargs": result.kwargs,
                    "result": result.result if result.status.value == "success" else None,
                    "error": result.error if result.status.value == "failed" else None,
                    "retries": result.retries,
                }
                for result in results
            ]

        except NotImplementedError:
            import logging
            logger = logging.getLogger("flowrra")
            logger.warning(
                f"Backend {backend.__class__.__name__} doesn't support list_by_status()"
            )
            return []
        except Exception as e:
            import logging
            logger = logging.getLogger("flowrra")
            logger.error(f"Failed to list {status.value} tasks: {e}")
            return []

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a completed task.

        Args:
            task_id: Task identifier

        Returns:
            Task result dictionary or None if not found:
            {
                "task_id": str,
                "status": str,
                "result": Any,
                "error": str | None,
                "completed_at": datetime | None
            }
        """
        result = await self.app.get_result(task_id)
        if not result:
            return None

        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result,
            "error": result.error,
            "completed_at": None,  # Not tracked yet
        }

    # ============================================
    # Scheduler Queries
    # ============================================

    async def list_schedules(
        self, enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """List all scheduled tasks.

        Args:
            enabled_only: If True, only return enabled schedules

        Returns:
            List of schedule dictionaries (empty if no scheduler configured)
        """
        if not self.app.scheduler:
            return []

        # Get schedules from backend
        if enabled_only:
            schedules = await self.app.scheduler.backend.list_enabled()
        else:
            schedules = await self.app.scheduler.backend.list_all()

        return [
            {
                "id": s.id,
                "task_name": s.task_name,
                "schedule_type": s.schedule_type.value,
                "schedule": s.schedule,
                "enabled": s.enabled,
                "next_run_at": s.next_run_at,
                "last_run_at": s.last_run_at,
                "priority": s.priority,
                "description": s.description,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in schedules
        ]

    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific schedule.

        Args:
            schedule_id: Schedule identifier

        Returns:
            Schedule dictionary or None if not found/no scheduler
        """
        if not self.app.scheduler:
            return None

        task = await self.app.scheduler.get_scheduled_task(schedule_id)
        if not task:
            return None

        return {
            "id": task.id,
            "task_name": task.task_name,
            "schedule_type": task.schedule_type.value,
            "schedule": task.schedule,
            "enabled": task.enabled,
            "next_run_at": task.next_run_at,
            "last_run_at": task.last_run_at,
            "priority": task.priority,
            "description": task.description,
            "args": task.args,
            "kwargs": task.kwargs,
            "max_retries": task.max_retries,
            "retry_delay": task.retry_delay,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    async def get_scheduler_stats(self) -> Optional[Dict[str, Any]]:
        """Get scheduler statistics.

        Returns:
            Scheduler stats dictionary or None if no scheduler
        """
        if not self.app.scheduler:
            return None

        all_schedules = await self.app.scheduler.backend.list_all()

        return {
            "running": self.app.scheduler.is_running,
            "check_interval": self.app.scheduler.check_interval,
            "total_schedules": len(all_schedules),
            "enabled_schedules": sum(1 for s in all_schedules if s.enabled),
            "disabled_schedules": sum(1 for s in all_schedules if not s.enabled),
        }

    # ============================================
    # Scheduler Management
    # ============================================

    async def create_schedule_cron(
        self,
        task_name: str,
        cron: str,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        enabled: bool = True,
        description: Optional[str] = None,
        priority: int = 0,
    ) -> str:
        """Create a cron-based schedule.

        Args:
            task_name: Name of registered task
            cron: Cron expression (e.g., "0 9 * * *")
            args: Positional arguments for task
            kwargs: Keyword arguments for task
            enabled: Whether schedule starts enabled
            description: Optional description
            priority: Task priority (higher = more important)

        Returns:
            Schedule ID

        Raises:
            ValueError: If no scheduler configured
        """
        if not self.app.scheduler:
            raise ValueError(
                "No scheduler configured. Create one with "
                "app.create_scheduler() first."
            )

        return await self.app.scheduler.schedule_cron(
            task_name=task_name,
            cron=cron,
            args=args,
            kwargs=kwargs or {},
            enabled=enabled,
            description=description,
            priority=priority,
        )

    async def create_schedule_interval(
        self,
        task_name: str,
        interval: float,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        enabled: bool = True,
        description: Optional[str] = None,
        priority: int = 0,
    ) -> str:
        """Create an interval-based schedule.

        Args:
            task_name: Name of registered task
            interval: Interval in seconds
            args: Positional arguments for task
            kwargs: Keyword arguments for task
            enabled: Whether schedule starts enabled
            description: Optional description
            priority: Task priority

        Returns:
            Schedule ID

        Raises:
            ValueError: If no scheduler configured
        """
        if not self.app.scheduler:
            raise ValueError(
                "No scheduler configured. Create one with "
                "app.create_scheduler() first."
            )

        return await self.app.scheduler.schedule_interval(
            task_name=task_name,
            interval=interval,
            args=args,
            kwargs=kwargs or {},
            enabled=enabled,
            description=description,
            priority=priority,
        )

    async def enable_schedule(self, schedule_id: str) -> None:
        """Enable a scheduled task.

        Args:
            schedule_id: Schedule identifier

        Raises:
            ValueError: If no scheduler configured or schedule not found
        """
        if not self.app.scheduler:
            raise ValueError("No scheduler configured")

        await self.app.scheduler.enable_task(schedule_id)

    async def disable_schedule(self, schedule_id: str) -> None:
        """Disable a scheduled task.

        Args:
            schedule_id: Schedule identifier

        Raises:
            ValueError: If no scheduler configured or schedule not found
        """
        if not self.app.scheduler:
            raise ValueError("No scheduler configured")

        await self.app.scheduler.disable_task(schedule_id)

    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a scheduled task.

        Args:
            schedule_id: Schedule identifier

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If no scheduler configured
        """
        if not self.app.scheduler:
            raise ValueError("No scheduler configured")

        return await self.app.scheduler.unschedule(schedule_id)

    # ============================================
    # Health Check
    # ============================================

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the Flowrra application.

        Returns:
            Health status dictionary:
            {
                "healthy": bool,
                "timestamp": datetime,
                "components": {
                    "app": {"healthy": bool, "message": str},
                    "io_executor": {"healthy": bool, "message": str} | None,
                    "cpu_executor": {"healthy": bool, "message": str} | None
                }
            }
        """
        components = {
            "app": self._check_app_health(),
            "io_executor": self._check_io_executor_health(),
            "cpu_executor": self._check_cpu_executor_health(),
            "scheduler": await self._check_scheduler_health(),
        }

        # Overall health: all components must be healthy (or None)
        healthy = all(
            comp is None or comp["healthy"] for comp in components.values()
        )

        return {
            "healthy": healthy,
            "timestamp": datetime.now(),
            "components": components,
        }

    def _check_app_health(self) -> Dict[str, Any]:
        """Check app health."""
        running = self.app.is_running
        return {
            "healthy": running,
            "message": "App is running" if running else "App is not running",
        }

    def _check_io_executor_health(self) -> Optional[Dict[str, Any]]:
        """Check IO executor health."""
        if not self.app._io_executor:
            return None

        running = self.app._io_executor.is_running
        return {
            "healthy": running,
            "message": "IO executor is running"
            if running
            else "IO executor is not running",
        }

    def _check_cpu_executor_health(self) -> Optional[Dict[str, Any]]:
        """Check CPU executor health."""
        if not self.app._cpu_executor:
            return None

        running = self.app._cpu_executor.is_running
        return {
            "healthy": running,
            "message": "CPU executor is running"
            if running
            else "CPU executor is not running",
        }

    async def _check_scheduler_health(self) -> Optional[Dict[str, Any]]:
        """Check scheduler health."""
        if not self.app.scheduler:
            return None

        running = self.app.scheduler.is_running
        return {
            "healthy": running,
            "message": "Scheduler is running" if running else "Scheduler is not running",
        }
