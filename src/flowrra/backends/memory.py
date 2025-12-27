"""In-memory result backend for single-process use."""

import asyncio

from flowrra.backends.base import BaseResultBackend
from flowrra.task import TaskResult


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
    
    def __len__(self) -> int:
        return len(self._results)
