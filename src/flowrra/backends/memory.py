"""In-memory result backend for single-process use."""

import asyncio
from datetime import datetime

from flowrra.backends.base import BaseResultBackend
from flowrra.task import TaskResult, TaskStatus


class InMemoryBackend(BaseResultBackend):
    """In-memory result storage.
    
    Best for:
    - Development and testing
    - Single-process applications
    - When persistence isn't needed
    
    Limitations:
    - Results lost on restart
    - Not shared across processes
    """

    def __init__(self):
        self._results: dict[str, TaskResult] = {}
        self._events: dict[str, asyncio.Event] = {}

    async def store(self, task_id: str, result: TaskResult) -> None:
        self._results[task_id] = result

        # Only set the event when task is complete (SUCCESS or FAILED)
        if task_id in self._events and result.is_complete:
            self._events[task_id].set()
    
    async def get(self, task_id: str) -> TaskResult | None:
        return self._results.get(task_id)
    
    async def wait_for(self, task_id: str, timeout: float | None) -> TaskResult:
        if task_id not in self._events:
            self._events[task_id] = asyncio.Event()

        result = self._results.get(task_id)
        if result and result.is_complete:
            return result

        await asyncio.wait_for(self._events[task_id].wait(), timeout=timeout)
        return self._results[task_id]
    
    async def delete(self, task_id: str) -> bool:
        if task_id in self._results:
            del self._results[task_id]
            self._events.pop(task_id, None)
            return True

        return False

    async def clear(self) -> int:
        count = len(self._results)
        self._results.clear()
        self._events.clear()
        return count

    async def list_by_status(
        self,
        status: TaskStatus,
        limit: int | None = None,
        offset: int = 0
    ) -> list[TaskResult]:
        """List tasks by status with optional pagination."""
        # Filter by status
        matching_tasks = [
            result for result in self._results.values()
            if result.status == status
        ]

        # Sort by submitted_at DESC (newest first)
        # Tasks without submitted_at go to the end
        matching_tasks.sort(
            key=lambda r: r.submitted_at if r.submitted_at else datetime.min,
            reverse=True
        )

        # Apply pagination
        start = offset
        end = offset + limit if limit is not None else None

        return matching_tasks[start:end]

    def __len__(self) -> int:
        return len(self._results)
