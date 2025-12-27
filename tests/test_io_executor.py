"""Tests for IOExecutor."""

import asyncio
import pytest
from flowrra import IOExecutor, Config, ExecutorConfig
from flowrra.task import TaskStatus
from flowrra.exceptions import ExecutorNotRunningError
from flowrra.backends.memory import InMemoryBackend


class TestIOExecutorBasics:
    """Basic IOExecutor tests."""

    def test_executor_creation(self):
        """Test creating an IOExecutor with config."""
        config = Config(executor=ExecutorConfig(num_workers=4))
        executor = IOExecutor(config=config)
        assert executor._num_workers == 4
        assert executor.is_running is False

    def test_executor_with_default_config(self):
        """Test executor with default config."""
        executor = IOExecutor()
        assert isinstance(executor.results, InMemoryBackend)
        assert executor._num_workers == 4  # Default from ExecutorConfig

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping executor."""
        config = Config(executor=ExecutorConfig(num_workers=2))
        executor = IOExecutor(config=config)

        assert executor.is_running is False
        await executor.start()
        assert executor.is_running is True

        await executor.stop()
        assert executor.is_running is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test executor as context manager."""
        config = Config(executor=ExecutorConfig(num_workers=2))
        executor = IOExecutor(config=config)

        async with executor:
            assert executor.is_running is True

        assert executor.is_running is False


class TestIOExecutorTasks:
    """Task execution tests."""

    @pytest.mark.asyncio
    async def test_simple_task(self):
        """Test executing a simple task."""
        config = Config(executor=ExecutorConfig(num_workers=2))
        executor = IOExecutor(config=config)

        @executor.task()
        async def add(a: int, b: int):
            return a + b

        async with executor:
            task_id = await executor.submit(add, 2, 3)
            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == 5

    @pytest.mark.asyncio
    async def test_task_with_sleep(self):
        """Test task with async sleep."""
        config = Config(executor=ExecutorConfig(num_workers=2))
        executor = IOExecutor(config=config)

        @executor.task()
        async def slow_task():
            await asyncio.sleep(0.1)
            return "done"

        async with executor:
            task_id = await executor.submit(slow_task)
            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == "done"

    @pytest.mark.asyncio
    async def test_multiple_tasks(self):
        """Test executing multiple tasks concurrently."""
        config = Config(executor=ExecutorConfig(num_workers=4))
        executor = IOExecutor(config=config)

        @executor.task()
        async def compute(x: int):
            await asyncio.sleep(0.05)
            return x * 2

        async with executor:
            task_ids = [await executor.submit(compute, i) for i in range(10)]
            results = [await executor.wait_for_result(tid, timeout=2.0) for tid in task_ids]

            assert all(r.status == TaskStatus.SUCCESS for r in results)
            assert [r.result for r in results] == [i * 2 for i in range(10)]

    @pytest.mark.asyncio
    async def test_task_with_exception(self):
        """Test task that raises an exception."""
        config = Config(executor=ExecutorConfig(num_workers=2))
        executor = IOExecutor(config=config)

        @executor.task(max_retries=0)
        async def failing_task():
            raise ValueError("Test error")

        async with executor:
            task_id = await executor.submit(failing_task)
            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.FAILED
            assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_task_retry(self):
        """Test task retry on failure."""
        config = Config(executor=ExecutorConfig(num_workers=2))
        executor = IOExecutor(config=config)

        call_count = 0

        @executor.task(max_retries=2, retry_delay=0.1)
        async def flaky_task():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        async with executor:
            task_id = await executor.submit(flaky_task)
            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == "success"
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_submit_without_start(self):
        """Test that submitting without starting raises error."""
        config = Config(executor=ExecutorConfig(num_workers=2))
        executor = IOExecutor(config=config)

        @executor.task()
        async def my_task():
            return "test"

        with pytest.raises(ExecutorNotRunningError):
            await executor.submit(my_task)
