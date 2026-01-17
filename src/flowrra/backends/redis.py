"""Redis-based result backend for distributed task execution."""

import asyncio
import json
from typing import Any

from flowrra.backends.base import BaseResultBackend
from flowrra.task import TaskResult, TaskStatus
from flowrra.exceptions import BackendError

try:
    import redis.asyncio as redis
except ImportError:
    redis = None


class RedisBackend(BaseResultBackend):
    """Redis-based result backend for distributed task execution.

    Features:
    - Cross-process result sharing
    - Persistent storage
    - Pub/sub for wait notifications
    - Automatic connection pooling
    - TTL support for result expiration

    Connection Patterns:
    - Basic: redis://localhost:6379/0
    - With password: redis://:password@localhost:6379/0
    - With username: redis://username:password@localhost:6379/0
    - SSL: rediss://localhost:6379/0
    - Unix socket: unix:///path/to/socket

    Args:
        url: Redis connection URL
        ttl: Optional TTL in seconds for result expiration (None = no expiration)
        **kwargs: Additional options passed to redis.asyncio.from_url()

    Example:
        backend = RedisBackend("redis://localhost:6379/0")
        backend = RedisBackend("redis://localhost:6379/0", ttl=3600)  # 1 hour expiration
    """

    def __init__(
        self,
        url: str,
        ttl: int | None = None,
        **kwargs: Any
    ):
        if redis is None:
            raise ImportError(
                "Redis backend requires redis package. "
                "Install with: pip install flowrra[redis]"
            )

        self._url = url
        self._ttl = ttl
        self._redis: redis.Redis | None = None
        self._kwargs = kwargs

    async def _ensure_connected(self) -> None:
        if self._redis is None:
            self._redis = await redis.from_url(
                self._url,
                decode_responses=True,
                **self._kwargs
            )

    def _get_task_key(self, task_id: str) -> str:
        return f"flowrra:task:{task_id}"

    def _get_complete_channel_name(self, task_id: str) -> str:
        """Generate Redis pub/sub channel name for task completion."""
        return f"flowrra:complete:{task_id}"

    async def store(self, task_id: str, result: TaskResult) -> None:
        await self._ensure_connected()

        try:
            data = json.dumps(result.to_dict)
            key = self._get_task_key(task_id)

            if self._ttl:
                await self._redis.setex(key, self._ttl, data)
            else:
                await self._redis.set(key, data)

            if result.is_complete:
                channel = self._get_complete_channel_name(task_id)
                await self._redis.publish(channel, "done")

        except Exception as e:
            raise BackendError(f"Failed to store task result: {e}") from e

    async def get(self, task_id: str) -> TaskResult | None:
        await self._ensure_connected()

        try:
            key = self._get_task_key(task_id)
            data = await self._redis.get(key)

            if data is None:
                return None

            return TaskResult.from_dict(json.loads(data))

        except Exception as e:
            raise BackendError(f"Failed to retrieve task result: {e}") from e

    async def wait_for(self, task_id: str, timeout: float | None = 10) -> TaskResult:
        """Wait for a task to complete using Redis pub/sub.

        Args:
            task_id: Unique task identifier
            timeout: Maximum seconds to wait (default is 10 sec)

        Returns:
            TaskResult when task completes

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        await self._ensure_connected()

        try:
            result = await self.get(task_id)
            if result and result.is_complete:
                return result

            pubsub = self._redis.pubsub()
            channel = self._get_complete_channel_name(task_id)
            await pubsub.subscribe(channel)

            try:
                async with asyncio.timeout(timeout):
                    async for message in pubsub.listen():
                        if message['type'] == 'message':
                            result = await self.get(task_id)
                            if result is None:
                                raise BackendError(
                                    f"Task {task_id} completed but result not found in Redis"
                                )

                            if not result.is_complete:
                                continue

                            return result

            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.close()

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            raise BackendError(f"Failed to wait for task result: {e}") from e

    async def delete(self, task_id: str) -> bool:
        """Delete a task result from Redis.

        Args:
            task_id: Unique task identifier

        Returns:
            True if deleted, False if not found
        """
        await self._ensure_connected()

        try:
            key = self._get_task_key(task_id)
            count = await self._redis.delete(key)
            return count > 0

        except Exception as e:
            raise BackendError(f"Failed to delete task result: {e}") from e

    async def clear(self) -> int:
        """Clear all Flowrra task results from Redis.

        Returns:
            Number of results cleared
        """
        await self._ensure_connected()

        try:
            pattern = "flowrra:task:*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self._redis.delete(*keys)
            return 0

        except Exception as e:
            raise BackendError(f"Failed to clear task results: {e}") from e

    async def list_by_status(
        self,
        status: TaskStatus,
        limit: int | None = None,
        offset: int = 0
    ) -> list[TaskResult]:
        """List tasks by status with optional pagination."""
        import logging
        from datetime import datetime

        logger = logging.getLogger("flowrra")

        await self._ensure_connected()

        try:
            # Collect all task keys
            pattern = "flowrra:task:*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern, count=100):
                keys.append(key)

            if not keys:
                return []

            # Batch fetch all task data
            raw_data = await self._redis.mget(keys)

            # Parse and filter by status
            matching_tasks = []
            for raw_json in raw_data:
                if raw_json is None:
                    continue

                try:
                    task_data = json.loads(raw_json)
                    result = TaskResult.from_dict(task_data)

                    if result.status == status:
                        matching_tasks.append(result)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse task result: {e}")
                    continue

            # Sort by submitted_at DESC (newest first)
            matching_tasks.sort(
                key=lambda r: r.submitted_at if r.submitted_at else datetime.min,
                reverse=True
            )

            # Apply pagination
            start = offset
            end = offset + limit if limit is not None else None

            return matching_tasks[start:end]

        except Exception as e:
            raise BackendError(f"Failed to list tasks by status: {e}") from e

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def __len__(self) -> int:
        """Not supported for Redis backend."""
        raise NotImplementedError(
            "len() not supported for RedisBackend. "
            "Use Redis commands to query key counts."
        )
