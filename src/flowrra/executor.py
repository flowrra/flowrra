import os
import asyncio
import uuid
import logging

from datetime import datetime
from typing import Callable
from concurrent.futures import ProcessPoolExecutor

from flowrra.task import Task, TaskResult, TaskStatus
from flowrra.registry import TaskRegistry
from flowrra.backends.base import BaseResultBackend
from flowrra.backends.memory import InMemoryBackend
from flowrra.exceptions import ExecutorNotRunningError

logger = logging.getLogger("flowrra")


class AsyncTaskExecutor:
    """Async task executor with configurable workers and backends.
    
    Usage:
        executor = AsyncTaskExecutor(num_workers=4)
        
        @executor.task()
        async def my_task(x):
            return x * 2
        
        await executor.start()
        task_id = await executor.submit(my_task, 42)
        result = await executor.wait_for_result(task_id)
        await executor.stop()
    """

    def __init__(
        self, 
        num_workers: int = 4, 
        cpu_workers: int | None = None,
        max_queue_size: int = 1000,
        backend: BaseResultBackend | None = None,
    ):
        """Initialize executor.
        
        Args:
            num_workers: Number of concurrent worker coroutines
            max_queue_size: Maximum pending tasks in queue
            backend: Result storage backend (defaults to InMemoryBackend)
        """

        self.registry = TaskRegistry()
        self.results = backend or InMemoryBackend()
        self._queue: asyncio.PriorityQueue[Task] = asyncio.PriorityQueue(max_queue_size)
        self._num_workers = num_workers
        self._cpu_workers = cpu_workers or os.cpu_count() or 4
        self._cpu_executor: ProcessPoolExecutor | None = None
        self._workers: list[asyncio.Task] = []
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def pending_count(self):
        return self._queue.qsize()
    
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

        # Verify task is registered
        self.registry.get_or_raise(task_name)

        task_id = str(uuid.uuid4())
        task = Task(
            id = task_id,
            name = task_name,
            args = args,
            kwargs = kwargs,
            max_retries = max_retries,
            retry_delay = retry_delay,
            priority = priority
        )

        # Initialize as pending
        await self.results.store(
            task_id, 
            TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        )

        await self._queue.put(task)
        logger.info(f"Submitted {task_name}[{task_id[:8]}]")
        return task_id
    
    async def _worker(self, worker_id: int):
        logger.debug(f"Worker-{worker_id} started")
        while True:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # If not running and queue is empty, exit
                if not self._running:
                    break
                continue

            try:
                await self._execute_task(task, worker_id)
            except asyncio.CancelledError:
                # Put task back if cancelled mid-execution
                await self._queue.put(task)
                raise
            finally:
                self._queue.task_done()

        logger.debug(f"Worker-{worker_id} stopped")

    async def _execute_task(self, task: Task, worker_id: int):
        """Execute a single task with retry logic."""
        task_func = self.registry.get(task.name)
        is_cpu_bound = getattr(task_func, "cpu_bound", False)

        # Initiate task result in running status
        result = TaskResult(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(),
            retries=task.current_retry,
        )

        await self.results.store(task.id, result)
        logger.info(f"Worker-{worker_id} running {task.name}[{task.id[:8]}]")

        try:
            if is_cpu_bound:
                # Lazy-initialize CPU executor on first use
                if self._cpu_executor is None:
                    self._cpu_executor = ProcessPoolExecutor(max_workers=self._cpu_workers)

                loop = asyncio.get_running_loop()
                from functools import partial
                func_with_args = partial(task_func, *task.args, **task.kwargs)
                output = await loop.run_in_executor(
                    self._cpu_executor,
                    func_with_args,
                )
            else:
                output = await task_func(*task.args, **task.kwargs)

            result.status = TaskStatus.SUCCESS
            result.result = output
            result.finished_at = datetime.now()
            await self.results.store(task.id, result)
            logger.info(f"Task {task.name}[{task.id[:8]}] succeeded")
        except Exception as e:
            if task.current_retry < task.max_retries:
                task.current_retry += 1
                result.status = TaskStatus.RETRYING
                result.retries = task.current_retry
                await self.results.store(task.id, result)

                logger.warning(
                    f"Task {task.name}[{task.id[:8]}] failed, "
                    f"retry {task.current_retry}/{task.max_retries} in {task.retry_delay}s"
                )

                await asyncio.sleep(task.retry_delay)
                await self._queue.put(task)
            else:
                result.status = TaskStatus.FAILED
                result.error = str(e)
                result.finished_at = datetime.now()
                await self.results.store(task.id, result)

                logger.error(f"Task {task.name}[{task.id[:8]}] failed: {e}")

    async def start(self):
        """Start the executor and worker pool."""
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self._num_workers)
        ]

        # CPU executor will be created lazily when first CPU-bound task is encountered

        logger.info(
            f'Executor started: '
            f'io_workers={self._num_workers}, '
            f'cpu_workers={self._cpu_workers}'
        )

    async def stop(self, wait: bool = True, timeout: float | None = 30.0):
        """Stop the executor.

        Args:
            wait: If True, wait for pending tasks to complete
            timeout: Max seconds to wait for pending tasks (default: 30.0)
        """
        if not self._running:
            return

        self._running = False

        if wait:
            try:
                await asyncio.wait_for(self._queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("Shutdown timeout, cancelling workers")

        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        if self._cpu_executor:
            self._cpu_executor.shutdown(wait=True)
            self._cpu_executor = None

        logger.info("Executor stopped")

    async def wait_for_result(
        self, 
        task_id: str, 
        timeout: float | None = None
    ) -> TaskResult:
        """Wait for a task to complete and return its result."""
        return await self.results.wait_for(task_id, timeout=timeout)
    
    async def get_result(self, task_id: str) -> TaskResult:
        return await self.results.get(task_id)
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
