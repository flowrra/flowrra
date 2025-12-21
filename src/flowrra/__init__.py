"""Flowrra - Async task executor built on asyncio.

A lightweight, Celery-inspired task queue using pure Python asyncio.

Basic usage:
    from flowrra import AsyncTaskExecutor
    
    executor = AsyncTaskExecutor(num_workers=4)
    
    @executor.task(max_retries=3)
    async def send_email(to: str, subject: str):
        # ... send email
        return {"sent": True}
    
    async def main():
        async with executor:
            task_id = await executor.submit(send_email, "user@example.com", "Hello")
            result = await executor.wait_for_result(task_id)
            print(result.result)

With custom backend (Redis support coming soon):
    from flowrra import AsyncTaskExecutor
    from flowrra.backends.memory import InMemoryBackend

    backend = InMemoryBackend()
    executor = AsyncTaskExecutor(backend=backend)
"""

__version__ = "0.1.0"

from flowrra.task import Task, TaskResult, TaskStatus
from flowrra.registry import TaskRegistry
from flowrra.executor import AsyncTaskExecutor
from flowrra.exceptions import (
    FlowrraError,
    TaskNotFoundError,
    TaskTimeoutError,
    ExecutorNotRunningError,
    BackendError,
)

__all__ = [
    # Core
    "AsyncTaskExecutor",
    "TaskRegistry",
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
