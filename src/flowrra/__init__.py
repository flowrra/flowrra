"""Flowrra - Async task executor built on asyncio.

A lightweight, Celery-inspired task queue using pure Python asyncio.

Basic usage with Flowrra (unified API):
    from flowrra import Flowrra

    app = Flowrra.from_urls(
        broker='redis://localhost:6379/0',
        backend='redis://localhost:6379/1'
    )

    # I/O-bound task (async)
    @app.task()
    async def fetch_data(url: str):
        return await fetch(url)

    # CPU-bound task (sync)
    @app.task(cpu_bound=True)
    def heavy_compute(n: int):
        return sum(i ** 2 for i in range(n))

    async def main():
        async with app:
            task_id = await app.submit(fetch_data, "https://api.example.com")
            result = await app.wait_for_result(task_id)
            print(result.result)

Advanced usage with IOExecutor and CPUExecutor:
    from flowrra import IOExecutor, CPUExecutor

    # For I/O-bound tasks only
    executor = IOExecutor(num_workers=10)

    # For CPU-bound tasks (requires Redis backend)
    executor = CPUExecutor(
        backend='redis://localhost:6379/0',
        cpu_workers=4
    )
"""

__version__ = "0.1.0"

from flowrra.app import Flowrra
from flowrra.task import Task, TaskResult, TaskStatus
from flowrra.registry import TaskRegistry
from flowrra.executors.io_executor import IOExecutor
from flowrra.executors.cpu_executor import CPUExecutor
from flowrra.config import Config, BrokerConfig, BackendConfig, ExecutorConfig
from flowrra.exceptions import (
    FlowrraError,
    TaskNotFoundError,
    TaskTimeoutError,
    ExecutorNotRunningError,
    BackendError,
)

__all__ = [
    # Main Application
    "Flowrra",
    # Executors (advanced usage)
    "IOExecutor",
    "CPUExecutor",
    "TaskRegistry",
    # Configuration
    "Config",
    "BrokerConfig",
    "BackendConfig",
    "ExecutorConfig",
    # Models
    "Task",
    "TaskResult",
    "TaskStatus",
    # Exceptions
    "FlowrraError",
    "TaskNotFoundError",
    "TaskTimeoutError",
    "ExecutorNotRunningError",
    "BackendError",
]
