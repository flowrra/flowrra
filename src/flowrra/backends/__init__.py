"""Flowrra result storage backends.

Available backends:
    - InMemoryBackend: Default, single-process, non-persistent (internal use only)
    - RedisBackend: Distributed, persistent (supports connection strings)

Factory function:
    - get_backend(): Create Redis backend from connection string or passthrough any backend instance

Usage:
    from flowrra import IOExecutor, CPUExecutor

    # IOExecutor: No backend needed (InMemoryBackend used internally)
    io_executor = IOExecutor(num_workers=4)

    # CPUExecutor: Redis connection string (recommended for production)
    cpu_executor = CPUExecutor(backend="redis://localhost:6379/0", cpu_workers=4)

Creating custom backends:
    Subclass BaseResultBackend and implement:
    - store(task_id, result)
    - get(task_id) -> TaskResult | None
    - wait_for(task_id, timeout) -> TaskResult

    Example:
        class PostgresBackend(BaseResultBackend):
            async def store(self, task_id, result): ...
            async def get(self, task_id): ...
            async def wait_for(self, task_id, timeout): ...
"""

from flowrra.backends.base import BaseResultBackend
from flowrra.backends.memory import InMemoryBackend
from flowrra.backends.factory import get_backend

try:
    from flowrra.backends.redis import RedisBackend
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

__all__ = [
    "BaseResultBackend",
    "InMemoryBackend",
    "get_backend",
]

if _HAS_REDIS:
    __all__.append("RedisBackend")
