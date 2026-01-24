"""I/O-bound task executor for async operations."""

import asyncio
import logging
from datetime import datetime

from flowrra.executors.base import BaseTaskExecutor
from flowrra.registry import TaskRegistry
from flowrra.task import Task, TaskResult, TaskStatus
from flowrra.config import Config

logger = logging.getLogger("flowrra")


class IOExecutor(BaseTaskExecutor):
    """Executor for I/O-bound async tasks.

    Best for:
    - Network requests (HTTP, database queries)
    - File I/O operations
    - API calls
    - Any async/await operations
    """

    def __init__(
        self,
        config: Config,
        registry: TaskRegistry | None = None
    ):
        """Initialize I/O executor.

        Args:
            config: Configuration object (optional, defaults to Config())
            registry: Shared TaskRegistry instance (optional, creates new if None)

        Example:
            # With full config
            from flowrra import Config, BrokerConfig, BackendConfig, ExecutorConfig

            config = Config(
                broker=BrokerConfig(url='redis://localhost:6379/0'),
                backend=BackendConfig(url='redis://localhost:6379/1'),
                executor=ExecutorConfig(num_workers=8)
            )
            executor = IOExecutor(config=config)

            # With default config (uses InMemoryBackend and asyncio.PriorityQueue)
            executor = IOExecutor()
        """
        num_workers = config.executor.num_workers

        super().__init__(config=config, registry=registry, queue_suffix=":io")
        self._num_workers = num_workers
        self._config = config

    def is_broker(self) -> bool:
        """Check if executor uses a broker for task queueing."""
        return self.broker is not None

    def task(self, name: str | None = None, max_retries: int = 3, retry_delay: float = 1.0):
        """Register an async I/O-bound task.

        Args:
            name: Custom task name (defaults to function name)
            max_retries: Max retry attempts on failure
            retry_delay: Seconds between retries

        Returns:
            Decorator function

        Raises:
            TypeError: If decorated function is not async or is CPU-bound
        """
        return self.registry.task(name=name, cpu_bound=False, max_retries=max_retries, retry_delay=retry_delay)

    async def _execute_task(self, task: Task, worker_id: int):
        """Execute an async I/O-bound task with retry logic.

        Args:
            task: Task to execute
            worker_id: ID of worker executing the task
        """
        task_func = self.registry.get(task.name)
        result = TaskResult(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(),
            retries=task.current_retry,
        )

        await self._store_and_emit(result)
        logger.info(f"Worker-{worker_id} running {task.name}[{task.id[:8]}]")

        try:
            output = await task_func(*task.args, **task.kwargs)

            result.status = TaskStatus.SUCCESS
            result.result = output
            result.finished_at = datetime.now()
            await self._store_and_emit(result)
            logger.info(f"Task {task.name}[{task.id[:8]}] succeeded")
        except Exception as e:
            if task.current_retry < task.max_retries:
                task.current_retry += 1
                result.status = TaskStatus.RETRYING
                result.retries = task.current_retry
                await self._store_and_emit(result)

                logger.warning(
                    f"Task {task.name}[{task.id[:8]}] failed, "
                    f"retry {task.current_retry}/{task.max_retries} in {task.retry_delay}s"
                )

                await asyncio.sleep(task.retry_delay)
                # Re-queue task for retry
                if self.broker is not None:
                    await self.broker.push(task)
                else:
                    await self._queue.put(task)
            else:
                result.status = TaskStatus.FAILED
                result.error = str(e)
                result.finished_at = datetime.now()
                await self._store_and_emit(result)

                logger.error(f"Task {task.name}[{task.id[:8]}] failed: {e}")

    async def start(self):
        """Start the I/O executor and worker pool."""
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self._num_workers)
        ]

        logger.info(f'IOExecutor started: io_workers={self._num_workers}')

    async def stop(self, wait: bool = True, timeout: float | None = 30.0):
        """Stop the I/O executor.

        Args:
            wait: If True, wait for pending tasks to complete
            timeout: Max seconds to wait for pending tasks (default: 30.0)
        """
        if not self._running:
            return

        self._running = False

        if wait and self._queue is not None:
            try:
                await asyncio.wait_for(self._queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("Shutdown timeout, cancelling workers")

        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        logger.info("IOExecutor stopped")
