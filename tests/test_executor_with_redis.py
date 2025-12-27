"""Integration tests for executors with Redis backend."""

import pytest
import asyncio
from flowrra import IOExecutor, CPUExecutor, Config, BackendConfig, ExecutorConfig
from flowrra.task import TaskStatus

pytestmark = pytest.mark.skipif(
    not __import__('importlib').util.find_spec('redis'),
    reason="Redis tests require 'redis' package"
)


@pytest.fixture
async def check_redis():
    """Skip if Redis not available."""
    try:
        import redis.asyncio as redis
        r = await redis.from_url("redis://localhost:6379/0")
        await r.ping()
        await r.aclose()
    except Exception:
        pytest.skip("Redis server not available")


@pytest.fixture
async def cleanup_redis():
    """Clean up Redis after test."""
    yield

    # Cleanup after test
    try:
        import redis.asyncio as redis
        r = await redis.from_url("redis://localhost:6379/0")
        # Delete all flowrra test keys
        keys = []
        async for key in r.scan_iter(match="flowrra:task:*"):
            keys.append(key)
        if keys:
            await r.delete(*keys)
        await r.aclose()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_io_executor_with_redis_string(check_redis, cleanup_redis):
    """Test IOExecutor with Redis connection string."""
    config = Config(
        backend=BackendConfig(url="redis://localhost:6379/0"),
        executor=ExecutorConfig(num_workers=2)
    )
    executor = IOExecutor(config=config)

    @executor.task()
    async def my_task(x: int):
        await asyncio.sleep(0.1)
        return x * 2

    async with executor:
        task_id = await executor.submit(my_task, 21)
        result = await executor.wait_for_result(task_id, timeout=2.0)

        assert result.status == TaskStatus.SUCCESS
        assert result.result == 42


@pytest.mark.asyncio
async def test_io_executor_default_backend_still_works(cleanup_redis):
    """Test IOExecutor with default backend (None) still uses InMemoryBackend."""
    config = Config(executor=ExecutorConfig(num_workers=2))
    executor = IOExecutor(config=config)

    @executor.task()
    async def my_task(x: int):
        return x * 3

    async with executor:
        task_id = await executor.submit(my_task, 10)
        result = await executor.wait_for_result(task_id, timeout=2.0)

        assert result.status == TaskStatus.SUCCESS
        assert result.result == 30


@pytest.mark.asyncio
async def test_cpu_executor_requires_backend():
    """Test CPUExecutor raises error when config lacks backend."""
    config = Config()  # No backend configured
    with pytest.raises(ValueError, match="requires backend configuration"):
        CPUExecutor(config=config)


@pytest.mark.asyncio
async def test_cpu_executor_with_redis_string_api(check_redis, cleanup_redis):
    """Test CPUExecutor accepts Redis connection string via config."""
    # Just test that it can be created with a string
    # We can't easily test execution since CPU tasks need to be module-level
    config = Config(
        backend=BackendConfig(url="redis://localhost:6379/0"),
        executor=ExecutorConfig(cpu_workers=2)
    )
    executor = CPUExecutor(config=config)

    # Verify executor was created successfully
    assert executor is not None
    assert executor._cpu_workers == 2


@pytest.mark.asyncio
async def test_io_executor_multiple_tasks_with_redis(check_redis, cleanup_redis):
    """Test IOExecutor with multiple tasks using Redis backend."""
    executor = IOExecutor(
        num_workers=3,
        backend="redis://localhost:6379/0"
    )

    @executor.task()
    async def add_numbers(a: int, b: int):
        await asyncio.sleep(0.1)
        return a + b

    async with executor:
        task_ids = []
        for i in range(5):
            task_id = await executor.submit(add_numbers, i, i * 2)
            task_ids.append(task_id)

        results = []
        for task_id in task_ids:
            result = await executor.wait_for_result(task_id, timeout=3.0)
            results.append(result)

        assert all(r.status == TaskStatus.SUCCESS for r in results)
        assert results[0].result == 0  # 0 + 0
        assert results[1].result == 3  # 1 + 2
        assert results[2].result == 6  # 2 + 4
        assert results[3].result == 9  # 3 + 6
        assert results[4].result == 12  # 4 + 8
