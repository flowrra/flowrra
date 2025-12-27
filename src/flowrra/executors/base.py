"""Base executor class with common functionality."""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Callable

from flowrra.registry import TaskRegistry
from flowrra.task import Task, TaskResult, TaskStatus
from flowrra.exceptions import ExecutorNotRunningError
from flowrra.config import Config

logger = logging.getLogger("flowrra")


class BaseTaskExecutor(ABC):
    """Abstract base class for task executors.

    Provides common functionality for task submission, queue management,
    worker lifecycle, and result storage. Subclasses must implement
    task execution logic specific to I/O-bound or CPU-bound tasks.
    """

    def __init__(self, config: Config):
        """Initialize base executor.

        Args:
            config: Configuration object (optional, defaults to Config())
        """
        self.registry = TaskRegistry()
        self.results = config.create_backend()
        self.broker = config.create_broker()

        max_queue_size = config.executor.max_queue_size

        if self.broker is None:
            self._queue: asyncio.PriorityQueue[Task] = asyncio.PriorityQueue(max_queue_size)
        else:
            self._queue = None

        self._workers: list[asyncio.Task] = []
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if executor is currently running."""
        return self._running

    @property
    def pending_count(self) -> int:
        """Get number of pending tasks in queue."""
        if self._queue is not None:
            return self._queue.qsize()
        else:
            # For broker-based queue, we can't get size synchronously
            # Return 0 or implement async method
            return 0

    def task(self, *args, **kwargs):
        """Decorator shortcut for self.registry.task()"""
        return self.registry.task(*args, **kwargs)

    async def submit(
        self,
        task_func: Callable,
        *args,
        priority: int = 0,
        **kwargs,
    ) -> str:
        """Submit a task for execution.

        Args:
            task_func: Registered task function
            *args: Positional arguments for the task
            priority: Lower number = higher priority (keyword-only)
            **kwargs: Keyword arguments for the task

        Returns:
            task_id: Unique identifier for tracking

        Raises:
            TaskNotFoundError: If task not registered
            ExecutorNotRunningError: If executor not started
        """
        if not self._running:
            raise ExecutorNotRunningError

        task_name = getattr(task_func, 'task_name', task_func.__name__)
        max_retries = getattr(task_func, 'max_retries', 3)
        retry_delay = getattr(task_func, 'retry_delay', 1.0)

        self.registry.get_or_raise(task_name)

        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=task_name,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries,
            retry_delay=retry_delay,
            priority=priority
        )

        # Initialize as pending
        await self.results.store(
            task_id,
            TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        )

        if self.broker is not None:
            await self.broker.push(task)
        else:
            await self._queue.put(task)

        logger.info(f"Submitted {task_name}[{task_id[:8]}]")
        return task_id

    async def _worker(self, worker_id: int):
        """Worker coroutine that processes tasks from the queue or broker.

        Args:
            worker_id: Unique identifier for this worker
        """
        logger.debug(f"Worker-{worker_id} started")
        while True:
            task = None
            try:
                if self.broker is not None:
                    task = await self.broker.pop(timeout=0.5)
                    if task is None:
                        if not self._running:
                            break
                        continue
                else:
                    task = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                if not self._running:
                    break
                continue

            try:
                await self._execute_task(task, worker_id)
            except asyncio.CancelledError:
                # Put task back if cancelled mid-execution
                if self.broker is not None:
                    await self.broker.push(task)
                else:
                    await self._queue.put(task)
                raise
            finally:
                if self._queue is not None:
                    self._queue.task_done()

        logger.debug(f"Worker-{worker_id} stopped")

    @abstractmethod
    async def _execute_task(self, task: Task, worker_id: int):
        """Execute a single task with retry logic.

        Subclasses must implement this method to define how tasks
        are executed (e.g., direct await for I/O, ProcessPoolExecutor for CPU).

        Args:
            task: Task to execute
            worker_id: ID of worker executing the task
        """
        pass

    @abstractmethod
    async def start(self):
        """Start the executor and worker pool.

        Subclasses must implement this to initialize any resources
        (e.g., worker tasks, process pools) needed for execution.
        """
        pass

    @abstractmethod
    async def stop(self, wait: bool = True, timeout: float | None = 30.0):
        """Stop the executor.

        Args:
            wait: If True, wait for pending tasks to complete
            timeout: Max seconds to wait for pending tasks

        Subclasses must implement this to clean up resources
        (e.g., cancel workers, shutdown process pools).
        """
        pass

    async def wait_for_result(
        self,
        task_id: str,
        timeout: float | None = None
    ) -> TaskResult:
        """Wait for a task to complete and return its result.

        Args:
            task_id: Task identifier
            timeout: Max seconds to wait (None = wait forever)

        Returns:
            TaskResult with status, result, and error information
        """
        return await self.results.wait_for(task_id, timeout=timeout)

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Get task result without waiting.

        Args:
            task_id: Task identifier

        Returns:
            TaskResult if available, None otherwise
        """
        return await self.results.get(task_id)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
