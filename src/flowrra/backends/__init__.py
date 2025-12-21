"""
Available backends:
    - InMemoryBackend: Default, single-process, non-persistent
    - RedisBackend: Distributed, persistent (requires `pip install redis`)

Creating custom backends:
    Subclass BaseResultBackend and implement:
    - store(task_id, result)
    - get(task_id) -> TaskResult | None
    - wait_for(task_id, timeout) -> TaskResult
    
Example:
    from taskex.backends import BaseResultBackend, InMemoryBackend, RedisBackend
    
    # Use in-memory (default)
    executor = AsyncTaskExecutor()
    
    # Use Redis
    executor = AsyncTaskExecutor(backend=RedisBackend("redis://localhost:6379"))
    
    # Custom backend
    class PostgresBackend(BaseResultBackend):
        async def store(self, task_id, result): ...
        async def get(self, task_id): ...
        async def wait_for(self, task_id, timeout): ...
"""

from flowrra.backends.base import BaseResultBackend
from flowrra.backends.memory import InMemoryBackend

__all__ = [
    "BaseResultBackend",
    "InMemoryBackend",
]
