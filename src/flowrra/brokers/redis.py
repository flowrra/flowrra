"""Redis-based broker for distributed task queueing."""

import json
import asyncio
from typing import Any

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from flowrra.brokers.base import BaseBroker
from flowrra.task import Task
from flowrra.exceptions import BackendError


class RedisBroker(BaseBroker):
    """Redis-based task queue broker.

    Uses Redis lists (LPUSH/BRPOP) for reliable task queueing.
    Tasks are serialized as JSON and pushed to a Redis list.

    Features:
    - Cross-process task distribution
    - Blocking pop with timeout support
    - Automatic connection pooling
    - Priority-based queueing (using task priority)

    Args:
        url: Redis connection string (e.g., 'redis://localhost:6379/0')
        max_connections: Maximum connections in pool (default: 50)
        socket_timeout: Socket timeout in seconds (default: 5.0)
        retry_on_timeout: Retry on connection timeout (default: True)
        queue_key: Redis key for task queue (default: 'flowrra:queue')
        **kwargs: Additional options passed to redis.asyncio.from_url()

    Example:
        broker = RedisBroker('redis://localhost:6379/0')

        # Push task
        task = Task(id='123', name='my_task', args=(1,), kwargs={})
        await broker.push(task)

        # Pop task (blocking)
        task = await broker.pop(timeout=5.0)
    """

    def __init__(
        self,
        url: str,
        max_connections: int = 50,
        socket_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        queue_key: str = "flowrra:queue",
        **kwargs: Any
    ):
        if redis is None:
            raise ImportError(
                "Redis broker requires redis package. "
                "Install with: pip install flowrra[redis]"
            )

        self._url = url
        self._max_connections = max_connections
        self._socket_timeout = socket_timeout
        self._retry_on_timeout = retry_on_timeout
        self._queue_key = queue_key
        self._redis: redis.Redis | None = None
        self._kwargs = kwargs

    async def _ensure_connected(self) -> None:
        """Lazy connection initialization."""
        if self._redis is None:
            try:
                self._redis = await redis.from_url(
                    self._url,
                    decode_responses=True,
                    max_connections=self._max_connections,
                    socket_timeout=self._socket_timeout,
                    retry_on_timeout=self._retry_on_timeout,
                    **self._kwargs
                )
            except Exception as e:
                raise BackendError(f"Failed to connect to Redis broker: {e}") from e

    async def push(self, task: Task) -> None:
        """Push a task to the Redis queue.

        Tasks are serialized as JSON and pushed to the left of the list (LPUSH).
        Priority is handled by using separate queues or sorting logic.

        Args:
            task: Task to queue

        Raises:
            BackendError: If Redis operation fails
        """
        await self._ensure_connected()

        try:
            task_data = {
                "id": task.id,
                "name": task.name,
                "args": task.args,
                "kwargs": task.kwargs,
                "max_retries": task.max_retries,
                "retry_delay": task.retry_delay,
                "current_retry": task.current_retry,
                "priority": task.priority,
                "cpu_bound": task.cpu_bound,
            }
            task_json = json.dumps(task_data)

            await self._redis.lpush(self._queue_key, task_json)

        except Exception as e:
            raise BackendError(f"Failed to push task to Redis queue: {e}") from e

    async def pop(self, timeout: float | None = None) -> Task | None:
        """Pop a task from the Redis queue.

        Uses BRPOP (blocking right pop) to wait for tasks efficiently.

        Args:
            timeout: Maximum time to wait in seconds (None = wait indefinitely)

        Returns:
            Task if available, None if timeout

        Raises:
            BackendError: If Redis operation fails
        """
        await self._ensure_connected()

        try:
            # timeout=0 means wait indefinitely
            redis_timeout = int(timeout) if timeout is not None else 0

            result = await self._redis.brpop(self._queue_key, timeout=redis_timeout)

            if result is None:
                return None

            _, task_json = result

            task_data = json.loads(task_json)

            task = Task(
                id=task_data["id"],
                name=task_data["name"],
                args=tuple(task_data["args"]),
                kwargs=task_data["kwargs"],
                max_retries=task_data["max_retries"],
                retry_delay=task_data["retry_delay"],
                current_retry=task_data["current_retry"],
                priority=task_data["priority"],
                cpu_bound=task_data.get("cpu_bound", False),  # Default to False for backward compatibility
            )

            return task

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            raise BackendError(f"Failed to pop task from Redis queue: {e}") from e

    async def size(self) -> int:
        """Get the number of tasks in the queue.

        Uses LLEN to get the length of the Redis list.

        Returns:
            Number of pending tasks

        Raises:
            BackendError: If Redis operation fails
        """
        await self._ensure_connected()

        try:
            size = await self._redis.llen(self._queue_key)
            return size

        except Exception as e:
            raise BackendError(f"Failed to get queue size from Redis: {e}") from e

    async def close(self) -> None:
        """Close Redis connections."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
