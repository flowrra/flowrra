"""Tests for CPUExecutor."""

import pytest
from flowrra import CPUExecutor, Config, BackendConfig, ExecutorConfig
from flowrra.task import TaskStatus
from flowrra.backends.memory import InMemoryBackend


class TestCPUExecutorBasics:
    """Basic CPUExecutor tests."""

    def test_executor_requires_config(self):
        """Test that CPUExecutor requires config parameter."""
        with pytest.raises(ValueError, match="requires config parameter"):
            CPUExecutor(config=None)

    def test_executor_requires_backend(self):
        """Test that CPUExecutor requires backend in config."""
        config = Config()  # No backend configured
        with pytest.raises(ValueError, match="requires backend configuration"):
            CPUExecutor(config=config)

    def test_executor_creation(self):
        """Test creating a CPUExecutor with config."""
        config = Config(
            backend=BackendConfig(url="redis://localhost:6379/0"),
            executor=ExecutorConfig(cpu_workers=4)
        )
        executor = CPUExecutor(config=config)
        assert isinstance(executor.results, InMemoryBackend) is False  # Should be RedisBackend
        assert executor._cpu_workers == 4

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping executor."""
        config = Config(
            backend=BackendConfig(url="redis://localhost:6379/0"),
            executor=ExecutorConfig(cpu_workers=2)
        )
        executor = CPUExecutor(config=config)

        assert executor.is_running is False
        await executor.start()
        assert executor.is_running is True

        await executor.stop()
        assert executor.is_running is False


class TestCPUExecutorTasks:
    """Task execution tests for CPU-bound tasks."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="CPU tasks require picklable functions - local functions not supported")
    async def test_simple_cpu_task(self):
        """Test executing a simple CPU-bound task."""
        config = Config(
            backend=BackendConfig(url="redis://localhost:6379/0"),
            executor=ExecutorConfig(cpu_workers=2)
        )
        executor = CPUExecutor(config=config)

        @executor.task()
        def compute(x: int):
            return x ** 2

        async with executor:
            task_id = await executor.submit(compute, 5)
            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == 25

    def test_cpu_task_must_be_sync(self):
        """Test that CPU tasks must be sync functions."""
        config = Config(
            backend=BackendConfig(url="redis://localhost:6379/0"),
            executor=ExecutorConfig(cpu_workers=2)
        )
        executor = CPUExecutor(config=config)

        # Should raise TypeError for async function
        with pytest.raises(TypeError, match="must be a sync function"):
            @executor.task()
            async def async_task():
                return "test"
