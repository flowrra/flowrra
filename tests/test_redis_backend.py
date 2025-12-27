"""Tests for Redis backend.

Requires Redis server running on localhost:6379.
Tests are skipped if redis package is not installed or server is unavailable.
"""

import pytest
import asyncio
from flowrra.task import TaskResult, TaskStatus
from datetime import datetime

try:
    from flowrra.backends.redis import RedisBackend
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

pytestmark = pytest.mark.skipif(
    not HAS_REDIS,
    reason="Redis tests require 'redis' package (pip install flowrra[redis])"
)


@pytest.fixture
async def redis_backend():
    """Create Redis backend and clean up after test."""
    backend = RedisBackend("redis://localhost:6379/0")

    yield backend

    # Cleanup
    await backend.clear()
    await backend.close()


@pytest.fixture
async def check_redis_available(redis_backend):
    """Skip test if Redis server is not available."""
    try:
        await redis_backend._ensure_connected()
        await redis_backend._redis.ping()
    except Exception:
        pytest.skip("Redis server not available at localhost:6379")


@pytest.mark.asyncio
async def test_redis_backend_store_and_get(redis_backend, check_redis_available):
    """Test storing and retrieving results."""
    result = TaskResult(
        task_id="test-123",
        status=TaskStatus.SUCCESS,
        result={"data": "value"},
        started_at=datetime.now(),
        finished_at=datetime.now()
    )

    await redis_backend.store("test-123", result)
    retrieved = await redis_backend.get("test-123")

    assert retrieved is not None
    assert retrieved.task_id == "test-123"
    assert retrieved.status == TaskStatus.SUCCESS
    assert retrieved.result == {"data": "value"}


@pytest.mark.asyncio
async def test_redis_backend_wait_for(redis_backend, check_redis_available):
    """Test waiting for task completion."""
    task_id = "test-wait-456"

    # Submit pending result
    pending_result = TaskResult(
        task_id=task_id,
        status=TaskStatus.PENDING
    )
    await redis_backend.store(task_id, pending_result)

    # Complete task in background after delay
    async def complete_task():
        await asyncio.sleep(0.5)
        complete_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.SUCCESS,
            result="completed"
        )
        await redis_backend.store(task_id, complete_result)

    # Start background completion
    asyncio.create_task(complete_task())

    # Wait for result
    result = await redis_backend.wait_for(task_id, timeout=2.0)

    assert result.status == TaskStatus.SUCCESS
    assert result.result == "completed"


@pytest.mark.asyncio
async def test_redis_backend_delete(redis_backend, check_redis_available):
    """Test deleting a result."""
    result = TaskResult(task_id="test-delete", status=TaskStatus.SUCCESS)
    await redis_backend.store("test-delete", result)

    deleted = await redis_backend.delete("test-delete")
    assert deleted is True

    retrieved = await redis_backend.get("test-delete")
    assert retrieved is None


@pytest.mark.asyncio
async def test_redis_backend_clear(redis_backend, check_redis_available):
    """Test clearing all results."""
    # Store multiple results
    for i in range(3):
        result = TaskResult(task_id=f"test-clear-{i}", status=TaskStatus.SUCCESS)
        await redis_backend.store(f"test-clear-{i}", result)

    # Clear all
    count = await redis_backend.clear()
    assert count >= 3  # At least the 3 we just added

    # Verify cleared
    for i in range(3):
        retrieved = await redis_backend.get(f"test-clear-{i}")
        assert retrieved is None


@pytest.mark.asyncio
async def test_redis_backend_ttl(check_redis_available):
    """Test result expiration with TTL."""
    backend = RedisBackend("redis://localhost:6379/0", ttl=1)  # 1 second TTL

    result = TaskResult(task_id="test-ttl", status=TaskStatus.SUCCESS)
    await backend.store("test-ttl", result)

    # Should exist immediately
    retrieved = await backend.get("test-ttl")
    assert retrieved is not None

    # Wait for expiration
    await asyncio.sleep(1.5)

    # Should be gone
    expired = await backend.get("test-ttl")
    assert expired is None

    await backend.close()


@pytest.mark.asyncio
async def test_redis_backend_wait_for_already_complete(redis_backend, check_redis_available):
    """Test wait_for when task is already complete."""
    task_id = "test-already-complete"

    # Store completed result
    complete_result = TaskResult(
        task_id=task_id,
        status=TaskStatus.SUCCESS,
        result="already done"
    )
    await redis_backend.store(task_id, complete_result)

    # wait_for should return immediately
    result = await redis_backend.wait_for(task_id, timeout=1.0)

    assert result.status == TaskStatus.SUCCESS
    assert result.result == "already done"
