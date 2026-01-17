"""Scheduler service for managing and executing scheduled tasks."""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Callable
import logging

from flowrra.scheduler.backends.base import BaseSchedulerBackend
from flowrra.scheduler.cron import CronExpression
from flowrra.scheduler.models import ScheduledTask, ScheduleType
from flowrra.registry import TaskRegistry

logger = logging.getLogger("flowrra.scheduler")


class Scheduler:
    """Scheduler service for persistent task scheduling.

    Features:
        - Cron-based scheduling
        - Interval-based scheduling
        - One-time task scheduling
        - Persistent storage across restarts
        - Automatic next-run calculation
        - Task priority support
        - Automatic routing to IOExecutor or CPUExecutor

    Args:
        backend: Scheduler storage backend
        registry: Task registry for resolving task names
        check_interval: How often to check for due tasks (seconds)
        io_executor: IOExecutor for async tasks (optional)
        cpu_executor: CPUExecutor for CPU-bound tasks (optional)

    Example:
        # Automatic integration with Flowrra app
        app = Flowrra.from_urls()
        scheduler = app.create_scheduler()

        # Manual setup
        scheduler = Scheduler(
            backend=backend,
            registry=registry,
            io_executor=io_executor,
            cpu_executor=cpu_executor
        )
    """

    def __init__(
        self,
        backend: BaseSchedulerBackend,
        registry: TaskRegistry,
        check_interval: float = 60.0,
        io_executor: "IOExecutor | None" = None,
        cpu_executor: "CPUExecutor | None" = None,
    ):
        """Initialize scheduler.

        Args:
            backend: Storage backend for scheduled tasks
            registry: Task registry for looking up task functions
            check_interval: Fallback interval in seconds (used on errors).
                           The scheduler uses dynamic sleep calculation by default,
                           waking up precisely when tasks are due. This parameter
                           is only used as a fallback when sleep calculation fails.
            io_executor: IOExecutor instance for async tasks
            cpu_executor: CPUExecutor instance for CPU-bound tasks

        Note:
            The scheduler automatically calculates optimal sleep duration based on
            when the next task is scheduled to run, with a maximum sleep of 1 hour
            to periodically refresh the schedule list.
        """
        self.backend = backend
        self.registry = registry
        self.check_interval = check_interval  # Fallback only
        self.io_executor = io_executor
        self.cpu_executor = cpu_executor
        self._running = False
        self._scheduler_task: asyncio.Task | None = None
        self._submit_callback: Callable | None = None

    def set_submit_callback(self, callback: Callable) -> None:
        """Set callback for submitting tasks to executor.

        LEGACY API: This method exists for backward compatibility and testing purposes.
        For production use, prefer passing executor instances to the constructor:

            scheduler = Scheduler(
                backend=backend,
                io_executor=io_executor,
                cpu_executor=cpu_executor
            )

        The callback approach bypasses executor-based task routing and requires
        manual implementation of submission logic. Use only when:
        - Writing unit tests that need to intercept submissions
        - Implementing custom submission logic outside the executor pattern

        Args:
            callback: Async function that accepts (task_func, *args, **kwargs)

        Example (Testing):
            async def track_submission(task_func, *args, **kwargs):
                submitted_tasks.append(task_func.__name__)

            scheduler.set_submit_callback(track_submission)

        Example (Modern Approach - Recommended):
            # Don't use callback - pass executors instead
            scheduler = Scheduler(backend, io_executor=io_executor)
            # Tasks automatically routed to correct executor
        """
        self._submit_callback = callback

    async def start(self) -> None:
        """Start the scheduler service."""
        if self._running:
            return

        if self._submit_callback is None and self.io_executor is None and self.cpu_executor is None:
            raise ValueError(
                "Scheduler requires either:\n"
                "1. Executor instances (RECOMMENDED): Pass io_executor and/or cpu_executor to constructor\n"
                "2. Submit callback (LEGACY): Call set_submit_callback() for testing/custom logic"
            )

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the scheduler service."""
        if not self._running:
            return

        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        await self.backend.close()

    async def schedule_cron(
        self,
        task_name: str,
        cron: str,
        args: tuple = (),
        kwargs: dict | None = None,
        enabled: bool = True,
        description: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        priority: int = 0,
        task_id: str | None = None,
    ) -> str:
        """Schedule a task using cron expression.

        Args:
            task_name: Name of registered task to execute
            cron: Cron expression (e.g., "0 9 * * *" for daily at 9 AM)
            args: Positional arguments for task
            kwargs: Keyword arguments for task
            enabled: Whether task is enabled
            description: Optional task description
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
            priority: Task priority (higher = more important)
            task_id: Optional custom task ID (generated if not provided)

        Returns:
            Task ID

        Raises:
            ValueError: If cron expression is invalid or task not registered
        """
        if not self.registry.is_registered(task_name):
            raise ValueError(f"Task '{task_name}' is not registered")

        # Validate cron expression
        cron_expr = CronExpression(cron)

        next_run = cron_expr.next_run()

        scheduled_task = ScheduledTask(
            id=task_id or str(uuid.uuid4()),
            task_name=task_name,
            schedule_type=ScheduleType.CRON,
            schedule=cron,
            args=args,
            kwargs=kwargs or {},
            enabled=enabled,
            next_run_at=next_run,
            description=description,
            max_retries=max_retries,
            retry_delay=retry_delay,
            priority=priority,
        )

        await self.backend.create(scheduled_task)
        return scheduled_task.id

    async def schedule_interval(
        self,
        task_name: str,
        interval: float,
        args: tuple = (),
        kwargs: dict | None = None,
        enabled: bool = True,
        description: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        priority: int = 0,
        task_id: str | None = None,
    ) -> str:
        """Schedule a task to run at fixed intervals.

        Args:
            task_name: Name of registered task to execute
            interval: Interval in seconds between executions
            args: Positional arguments for task
            kwargs: Keyword arguments for task
            enabled: Whether task is enabled
            description: Optional task description
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
            priority: Task priority (higher = more important)
            task_id: Optional custom task ID (generated if not provided)

        Returns:
            Task ID

        Raises:
            ValueError: If interval is invalid or task not registered
        """
        if not self.registry.is_registered(task_name):
            raise ValueError(f"Task '{task_name}' is not registered")

        if interval <= 0:
            raise ValueError("Interval must be positive")

        # Calculate next run
        next_run = datetime.now() + timedelta(seconds=interval)

        scheduled_task = ScheduledTask(
            id=task_id or str(uuid.uuid4()),
            task_name=task_name,
            schedule_type=ScheduleType.INTERVAL,
            schedule=str(interval),
            args=args,
            kwargs=kwargs or {},
            enabled=enabled,
            next_run_at=next_run,
            description=description,
            max_retries=max_retries,
            retry_delay=retry_delay,
            priority=priority,
        )

        await self.backend.create(scheduled_task)
        return scheduled_task.id

    async def schedule_once(
        self,
        task_name: str,
        run_at: datetime,
        args: tuple = (),
        kwargs: dict | None = None,
        description: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        priority: int = 0,
        task_id: str | None = None,
    ) -> str:
        """Schedule a task to run once at a specific time.

        Args:
            task_name: Name of registered task to execute
            run_at: When to run the task
            args: Positional arguments for task
            kwargs: Keyword arguments for task
            description: Optional task description
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
            priority: Task priority (higher = more important)
            task_id: Optional custom task ID (generated if not provided)

        Returns:
            Task ID

        Raises:
            ValueError: If task not registered
        """
        if not self.registry.is_registered(task_name):
            raise ValueError(f"Task '{task_name}' is not registered")

        scheduled_task = ScheduledTask(
            id=task_id or str(uuid.uuid4()),
            task_name=task_name,
            schedule_type=ScheduleType.ONE_TIME,
            schedule=run_at.isoformat(),
            args=args,
            kwargs=kwargs or {},
            enabled=True,
            next_run_at=run_at,
            description=description,
            max_retries=max_retries,
            retry_delay=retry_delay,
            priority=priority,
        )

        await self.backend.create(scheduled_task)
        return scheduled_task.id

    async def unschedule(self, task_id: str) -> bool:
        """Remove a scheduled task.

        Args:
            task_id: ID of task to remove

        Returns:
            True if deleted, False if not found
        """
        return await self.backend.delete(task_id)

    async def enable_task(self, task_id: str) -> None:
        """Enable a scheduled task.

        Args:
            task_id: ID of task to enable

        Raises:
            ValueError: If task not found
        """
        task = await self.backend.get(task_id)
        if task is None:
            raise ValueError(f"Scheduled task '{task_id}' not found")

        task.enabled = True
        await self.backend.update(task)

    async def disable_task(self, task_id: str) -> None:
        """Disable a scheduled task.

        Args:
            task_id: ID of task to disable

        Raises:
            ValueError: If task not found
        """
        task = await self.backend.get(task_id)
        if task is None:
            raise ValueError(f"Scheduled task '{task_id}' not found")

        task.enabled = False
        await self.backend.update(task)

    async def get_scheduled_task(self, task_id: str) -> ScheduledTask | None:
        """Get a scheduled task by ID.

        Args:
            task_id: Task ID

        Returns:
            ScheduledTask if found, None otherwise
        """
        return await self.backend.get(task_id)

    async def list_scheduled_tasks(self) -> list[ScheduledTask]:
        """List all scheduled tasks.

        Returns:
            List of all ScheduledTask objects
        """
        return await self.backend.list_all()

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that checks for and executes due tasks.

        The scheduler uses dynamic sleep calculation to wake up precisely when
        tasks are due, rather than polling at fixed intervals. This reduces
        resource usage and improves scheduling accuracy.
        """
        while self._running:
            try:
                await self._check_and_execute_due_tasks()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            # Max sleep is 1 hour to periodically refresh schedules
            sleep_duration = await self._calculate_next_wake_time(max_sleep=3600.0)

            if sleep_duration >= 3600.0:
                logger.debug("No tasks due within 1 hour, sleeping for maximum duration")
            elif sleep_duration <= 1.0:
                logger.debug(f"Task due very soon, sleeping for {sleep_duration:.1f}s")
            else:
                logger.debug(f"Next task due in {sleep_duration:.1f}s, sleeping until then")

            try:
                await asyncio.sleep(sleep_duration)
            except asyncio.CancelledError:
                # Scheduler is being stopped
                break

    async def _check_and_execute_due_tasks(self) -> None:
        """Check for due tasks and execute them."""
        now = datetime.now()
        due_tasks = await self.backend.list_due(now)

        for scheduled_task in due_tasks:
            try:
                await self._execute_scheduled_task(scheduled_task, now)
            except Exception as e:
                logger.error(f"Error executing scheduled task {scheduled_task.id}: {e}")

    async def _submit_task_to_executor(
        self,
        task_func: Callable,
        *args,
        **kwargs
    ) -> str | None:
        """Submit task to appropriate executor based on cpu_bound attribute.

        Args:
            task_func: Task function to execute
            *args: Positional arguments for task
            **kwargs: Keyword arguments for task

        Returns:
            Task ID if submitted successfully, None otherwise
        """
        is_cpu_bound = getattr(task_func, 'cpu_bound', False)

        if is_cpu_bound:
            if self.cpu_executor is None:
                logger.warning(f"CPU-bound task '{task_func.task_name}' scheduled but no CPUExecutor provided")
                return None

            if not self.cpu_executor.is_running:
                logger.warning(f"CPUExecutor not running for task '{task_func.task_name}'")
                return None

            return await self.cpu_executor.submit(task_func, *args, **kwargs)
        else:
            if self.io_executor is None:
                logger.warning(f"IO-bound task '{task_func.task_name}' scheduled but no IOExecutor provided")
                return None

            if not self.io_executor.is_running:
                logger.warning(f"IOExecutor not running for task '{task_func.task_name}'")
                return None

            return await self.io_executor.submit(task_func, *args, **kwargs)

    async def _execute_scheduled_task(self, scheduled_task: ScheduledTask, now: datetime) -> None:
        """Execute a scheduled task and update its next run time.

        Args:
            scheduled_task: Task to execute
            now: Current time
        """
        task_func = self.registry.get(scheduled_task.task_name)
        if task_func is None:
            logger.warning(f"Task '{scheduled_task.task_name}' not found in registry, skipping")
            return

        # Priority 1: Use callback if set (backward compatibility)
        if self._submit_callback:
            try:
                await self._submit_callback(task_func, *scheduled_task.args, **scheduled_task.kwargs)
            except Exception as e:
                logger.error(f"Error submitting task {scheduled_task.task_name} via callback: {e}")
        # Priority 2: Use automatic executor routing
        elif self.io_executor is not None or self.cpu_executor is not None:
            try:
                task_id = await self._submit_task_to_executor(
                    task_func,
                    *scheduled_task.args,
                    **scheduled_task.kwargs
                )
                if task_id:
                    logger.info(f"Scheduled task {scheduled_task.task_name} submitted with ID {task_id}")
            except Exception as e:
                logger.error(f"Error submitting task {scheduled_task.task_name} to executor: {e}")
        else:
            logger.warning(f"No executor or callback configured for task {scheduled_task.task_name}")
            return

        next_run = self._calculate_next_run(scheduled_task, now)

        if next_run:
            await self.backend.update_run_times(scheduled_task.id, now, next_run)
        else:
            # One-time task, disable after execution
            scheduled_task.enabled = False
            scheduled_task.last_run_at = now
            await self.backend.update(scheduled_task)

    def _calculate_next_run(self, scheduled_task: ScheduledTask, now: datetime) -> datetime | None:
        """Calculate the next run time for a scheduled task.

        Args:
            scheduled_task: Task to calculate next run for
            now: Current time

        Returns:
            Next run datetime, or None for one-time tasks
        """
        if scheduled_task.schedule_type == ScheduleType.CRON:
            cron_expr = CronExpression(scheduled_task.schedule)
            return cron_expr.next_run(now)

        elif scheduled_task.schedule_type == ScheduleType.INTERVAL:
            interval = float(scheduled_task.schedule)
            return now + timedelta(seconds=interval)

        else:  # ONE_TIME
            return None

    async def _calculate_next_wake_time(self, max_sleep: float = 3600.0) -> float:
        """Calculate optimal sleep duration until next scheduled task.

        Args:
            max_sleep: Maximum sleep duration in seconds (default 1 hour)

        Returns:
            Sleep duration in seconds (minimum 1.0, maximum max_sleep)

        Strategy:
            1. Query all enabled schedules
            2. Find earliest next_run_at
            3. Calculate time difference from now
            4. Apply min/max bounds
        """
        try:
            # Get all enabled schedules with their next_run_at times
            enabled_tasks = await self.backend.list_enabled()

            if not enabled_tasks:
                # No tasks scheduled - sleep for max duration
                return max_sleep

            # Find earliest next_run_at among all enabled tasks
            now = datetime.now()
            next_run_times = [
                task.next_run_at for task in enabled_tasks
                if task.next_run_at is not None
            ]

            if not next_run_times:
                # No tasks have next_run_at set - sleep for max duration
                return max_sleep

            earliest_next_run = min(next_run_times)

            # Calculate seconds until earliest task
            time_until_next = (earliest_next_run - now).total_seconds()

            # Handle edge cases
            if time_until_next <= 0:
                # Task is overdue - check immediately
                return 0.1  # Small delay to avoid tight loop
            elif time_until_next < 1.0:
                # Task due very soon - wait briefly
                return 1.0
            elif time_until_next > max_sleep:
                # Task far in future - cap at max sleep
                return max_sleep
            else:
                # Normal case - sleep until task is due
                return time_until_next

        except Exception as e:
            # On error, fall back to check_interval
            logger.error(f"Error calculating next wake time: {e}")
            return min(self.check_interval, max_sleep)

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
