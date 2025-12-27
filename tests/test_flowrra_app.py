"""Tests for the unified Flowrra application class."""

import pytest
from flowrra import Flowrra, Config, BrokerConfig, ExecutorConfig
from flowrra.task import TaskStatus


class TestFlowrraBasic:
    """Test basic Flowrra functionality."""

    @pytest.mark.asyncio
    async def test_flowrra_creation(self):
        """Test creating Flowrra instance."""
        app = Flowrra()

        assert app is not None
        assert app._config is not None
        assert not app.is_running

    @pytest.mark.asyncio
    async def test_flowrra_from_urls(self):
        """Test Flowrra.from_urls() convenience method."""
        app = Flowrra.from_urls()

        assert app is not None
        assert app._config is not None

    @pytest.mark.asyncio
    async def test_flowrra_with_config(self):
        """Test Flowrra with Config."""
        config = Config(
            executor=ExecutorConfig(num_workers=4)
        )
        app = Flowrra(config=config)

        assert app._config == config


class TestFlowrraIOTasks:
    """Test Flowrra with I/O-bound tasks."""

    @pytest.mark.asyncio
    async def test_io_task_registration(self):
        """Test registering I/O-bound task."""
        app = Flowrra()

        @app.task()
        async def simple_task(x: int):
            return x * 2

        # Should have registered in IO executor
        assert app._io_executor is not None
        assert app._cpu_executor is None

    @pytest.mark.asyncio
    async def test_io_task_execution(self):
        """Test executing I/O-bound task."""
        app = Flowrra()

        @app.task()
        async def add_numbers(a: int, b: int):
            return a + b

        async with app:
            task_id = await app.submit(add_numbers, 10, 20)
            result = await app.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == 30

    @pytest.mark.asyncio
    async def test_multiple_io_tasks(self):
        """Test executing multiple I/O-bound tasks."""
        app = Flowrra()

        @app.task()
        async def multiply(x: int):
            return x * 2

        @app.task()
        async def square(x: int):
            return x ** 2

        async with app:
            task1 = await app.submit(multiply, 5)
            task2 = await app.submit(square, 3)

            result1 = await app.wait_for_result(task1, timeout=2.0)
            result2 = await app.wait_for_result(task2, timeout=2.0)

            assert result1.result == 10
            assert result2.result == 9


class TestFlowrraTaskRetries:
    """Test Flowrra task retry behavior."""

    @pytest.mark.asyncio
    async def test_task_with_retries(self):
        """Test task with custom retry settings."""
        app = Flowrra()

        @app.task(max_retries=5, retry_delay=0.1)
        async def custom_retry_task(x: int):
            return x * 3

        async with app:
            task_id = await app.submit(custom_retry_task, 7)
            result = await app.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == 21


class TestFlowrraContextManager:
    """Test Flowrra context manager behavior."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using Flowrra as context manager."""
        app = Flowrra()

        @app.task()
        async def test_task():
            return "success"

        assert not app.is_running

        async with app:
            assert app.is_running
            task_id = await app.submit(test_task)
            result = await app.wait_for_result(task_id, timeout=2.0)
            assert result.result == "success"

        assert not app.is_running


class TestFlowrraGetResult:
    """Test Flowrra get_result functionality."""

    @pytest.mark.asyncio
    async def test_get_result_immediate(self):
        """Test getting result without waiting."""
        app = Flowrra()

        @app.task()
        async def quick_task():
            return "done"

        async with app:
            task_id = await app.submit(quick_task)

            # Wait for completion
            await app.wait_for_result(task_id, timeout=2.0)

            # Get result without waiting
            result = await app.get_result(task_id)
            assert result is not None
            assert result.result == "done"

    @pytest.mark.asyncio
    async def test_get_result_not_found(self):
        """Test getting result for non-existent task."""
        app = Flowrra()

        @app.task()
        async def dummy_task():
            return "test"

        async with app:
            result = await app.get_result("non-existent-task-id")
            assert result is None


class TestFlowrraWithBrokerConfig:
    """Test Flowrra with broker configuration."""

    @pytest.mark.asyncio
    async def test_flowrra_accepts_broker_config(self):
        """Test Flowrra accepts broker config (even if Redis not available)."""
        config = Config(
            broker=BrokerConfig(url='redis://localhost:6379/0')
        )
        app = Flowrra(config=config)

        assert app._config.broker is not None
        assert app._config.broker.url == 'redis://localhost:6379/0'

    @pytest.mark.asyncio
    async def test_flowrra_from_urls_with_broker(self):
        """Test Flowrra.from_urls() with broker."""
        app = Flowrra.from_urls(
            broker='redis://localhost:6379/0',
            backend='redis://localhost:6379/1'
        )

        assert app._config.broker is not None
        assert app._config.broker.url == 'redis://localhost:6379/0'
        assert app._config.backend is not None
        assert app._config.backend.url == 'redis://localhost:6379/1'
