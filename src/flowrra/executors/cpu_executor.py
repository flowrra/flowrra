"""CPU-bound task executor using ProcessPoolExecutor."""

import asyncio
import logging
import os
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from flowrra.executors.base import BaseTaskExecutor
from flowrra.registry import TaskRegistry
from flowrra.task import Task, TaskResult, TaskStatus
from flowrra.config import Config

logger = logging.getLogger("flowrra")


class CPUExecutor(BaseTaskExecutor):
    """Executor for CPU-bound sync tasks using ProcessPoolExecutor.

    Best for:
    - Heavy computations
    - Data processing
    - Image/video processing
    - Scientific calculations
    - Cryptographic operations

    Important:
    - Tasks must be regular (sync) functions, NOT async
    - Requires explicit backend for cross-process result sharing
    - Tasks must be picklable (no local functions)

    Usage:
        from flowrra import Config, BackendConfig, ExecutorConfig

        config = Config(
            backend=BackendConfig(url="redis://localhost:6379/0"),
            executor=ExecutorConfig(cpu_workers=4)
        )
        executor = CPUExecutor(config=config)

        @executor.task()
        def heavy_computation(n: int):
            # CPU-intensive work
            return sum(i ** 2 for i in range(n))

        async with executor:
            task_id = await executor.submit(heavy_computation, 1000000)
            result = await executor.wait_for_result(task_id)
    """

    def __init__(self, config: Config, registry: TaskRegistry | None = None):
        """Initialize CPU executor.

        Args:
            config: Config object (REQUIRED) with backend configuration
            registry: Shared TaskRegistry instance (optional, creates new if None)

        Raises:
            ValueError: If config is None or config lacks backend

        Example:
            from flowrra import Config, BackendConfig, ExecutorConfig
            config = Config(
                backend=BackendConfig(url="redis://localhost:6379/0"),
                executor=ExecutorConfig(cpu_workers=4, max_queue_size=1000)
            )
            executor = CPUExecutor(config=config)
        """
        if config.backend is None:
            raise ValueError(
                "CPUExecutor requires backend configuration for cross-process result sharing.\n"
                "Example: Config(backend=BackendConfig(url='redis://localhost:6379/0'))"
            )

        super().__init__(config=config, registry=registry, queue_suffix=":cpu")
        self._cpu_workers = config.executor.cpu_workers or os.cpu_count() or 4
        self._cpu_executor: ProcessPoolExecutor | None = None
        self._io_workers = 1  # Single asyncio worker to manage process pool

    def task(self, name: str | None = None, max_retries: int = 3, retry_delay: float = 1.0):
        """Register a sync CPU-bound task.

        Args:
            name: Custom task name (defaults to function name)
            max_retries: Max retry attempts on failure
            retry_delay: Seconds between retries

        Returns:
            Decorator function

        Raises:
            TypeError: If decorated function is async
        """
        return self.registry.task(name=name, cpu_bound=True, max_retries=max_retries, retry_delay=retry_delay)

    async def _execute_task(self, task: Task, worker_id: int):
        """Execute a CPU-bound task in ProcessPoolExecutor with retry logic.

        Args:
            task: Task to execute
            worker_id: ID of worker executing the task
        """
        task_func = self.registry.get(task.name)

        if self._cpu_executor is None:
            self._cpu_executor = ProcessPoolExecutor(max_workers=self._cpu_workers)
            logger.debug(f"Initialized ProcessPoolExecutor with {self._cpu_workers} workers")

        result = TaskResult(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(),
            retries=task.current_retry,
        )

        await self._store_and_emit(result)
        logger.info(f"Worker-{worker_id} running {task.name}[{task.id[:8]}] in process pool")

        try:
            # Execute CPU-bound task in process pool
            loop = asyncio.get_running_loop()
            func_with_args = partial(task_func, *task.args, **task.kwargs)
            output = await loop.run_in_executor(
                self._cpu_executor,
                func_with_args,
            )

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
                # Re-submit for retry
                if self._queue is not None:
                    await self._queue.put(task)
                elif self.broker is not None:
                    await self.broker.push(task)
                else:
                    logger.error(f"Cannot retry task {task.name}[{task.id[:8]}]: no queue or broker available")
            else:
                result.status = TaskStatus.FAILED
                result.error = str(e)
                result.finished_at = datetime.now()
                await self._store_and_emit(result)

                logger.error(f"Task {task.name}[{task.id[:8]}] failed: {e}")

    async def start(self):
        """Start the CPU executor and worker pool."""
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self._io_workers)
        ]

        logger.info(f'CPUExecutor started: cpu_workers={self._cpu_workers}')

    async def stop(self, wait: bool = True, timeout: float | None = 30.0):
        """Stop the CPU executor.

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

        if self._cpu_executor:
            self._cpu_executor.shutdown(wait=True)
            self._cpu_executor = None
            logger.debug("ProcessPoolExecutor shutdown complete")

        logger.info("CPUExecutor stopped")
