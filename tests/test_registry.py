"""Tests for task registry."""

import asyncio
import pytest
from flowrra.registry import TaskRegistry
from flowrra.exceptions import TaskNotFoundError


class TestTaskRegistry:
    """Tests for TaskRegistry."""

    def test_registry_initialization(self):
        """Test registry starts empty."""
        registry = TaskRegistry()

        assert len(registry) == 0
        assert registry.list_tasks() == []

    def test_register_async_task(self):
        """Test registering an async task."""
        registry = TaskRegistry()

        @registry.task(name=None, max_retries=3, retry_delay=1.0)
        async def my_task(x: int) -> int:
            return x * 2

        assert len(registry) == 1
        assert "my_task" in registry
        assert registry.is_registered("my_task")
        assert "my_task" in registry.list_tasks()

    def test_register_task_with_custom_name(self):
        """Test registering a task with a custom name."""
        registry = TaskRegistry()

        @registry.task(name="custom_name")
        async def my_function():
            return "hello"

        assert "custom_name" in registry
        assert "my_function" not in registry

    def test_register_sync_cpu_bound_task(self):
        """Test registering a sync CPU-bound task."""
        registry = TaskRegistry()

        @registry.task(name=None, cpu_bound=True)
        def compute(n: int) -> int:
            return sum(range(n))

        assert "compute" in registry
        task_func = registry.get("compute")
        assert task_func.cpu_bound is True

    def test_reject_async_cpu_bound_task(self):
        """Test that async functions are rejected for CPU-bound tasks."""
        registry = TaskRegistry()

        with pytest.raises(TypeError, match="must be a sync function"):

            @registry.task(name=None, cpu_bound=True)
            async def bad_task():
                return 42

    def test_reject_sync_io_bound_task(self):
        """Test that sync functions are rejected for I/O-bound tasks."""
        registry = TaskRegistry()

        with pytest.raises(TypeError, match="must be an async function"):

            @registry.task(name=None, cpu_bound=False)
            def bad_task():
                return 42

    def test_task_attributes(self):
        """Test that task metadata is attached correctly."""
        registry = TaskRegistry()

        @registry.task(name="test_task", max_retries=5, retry_delay=2.5)
        async def my_task():
            return "done"

        task_func = registry.get("test_task")
        assert task_func.task_name == "test_task"
        assert task_func.max_retries == 5
        assert task_func.retry_delay == 2.5
        assert task_func.cpu_bound is False

    def test_get_task(self):
        """Test getting a registered task."""
        registry = TaskRegistry()

        @registry.task(name=None)
        async def my_task():
            return 123

        task = registry.get("my_task")
        assert task is not None
        assert asyncio.iscoroutinefunction(task)

    def test_get_nonexistent_task(self):
        """Test getting a task that doesn't exist."""
        registry = TaskRegistry()

        result = registry.get("nonexistent")
        assert result is None

    def test_get_or_raise(self):
        """Test get_or_raise with existing task."""
        registry = TaskRegistry()

        @registry.task(name=None)
        async def my_task():
            return 456

        task = registry.get_or_raise("my_task")
        assert task is not None

    def test_get_or_raise_nonexistent(self):
        """Test get_or_raise raises for nonexistent task."""
        registry = TaskRegistry()

        with pytest.raises(TaskNotFoundError, match="'missing_task' not registered"):
            registry.get_or_raise("missing_task")

    def test_unregister_task(self):
        """Test unregistering a task."""
        registry = TaskRegistry()

        @registry.task(name=None)
        async def my_task():
            return 789

        assert "my_task" in registry
        assert len(registry) == 1

        result = registry.unregister("my_task")
        assert result is True
        assert "my_task" not in registry
        assert len(registry) == 0

    def test_unregister_nonexistent_task(self):
        """Test unregistering a task that doesn't exist."""
        registry = TaskRegistry()

        result = registry.unregister("nonexistent")
        assert result is False

    def test_multiple_tasks(self):
        """Test registering multiple tasks."""
        registry = TaskRegistry()

        @registry.task(name=None)
        async def task1():
            return 1

        @registry.task(name=None)
        async def task2():
            return 2

        @registry.task(name=None, cpu_bound=True)
        def task3():
            return 3

        assert len(registry) == 3
        assert "task1" in registry
        assert "task2" in registry
        assert "task3" in registry

        tasks = registry.list_tasks()
        assert set(tasks) == {"task1", "task2", "task3"}

    @pytest.mark.asyncio
    async def test_async_task_execution(self):
        """Test that registered async tasks can be executed."""
        registry = TaskRegistry()

        @registry.task(name=None)
        async def add(a: int, b: int) -> int:
            return a + b

        task_func = registry.get("add")
        result = await task_func(10, 20)
        assert result == 30

    def test_sync_cpu_task_execution(self):
        """Test that registered sync tasks can be executed."""
        registry = TaskRegistry()

        @registry.task(name=None, cpu_bound=True)
        def multiply(a: int, b: int) -> int:
            return a * b

        task_func = registry.get("multiply")
        result = task_func(5, 7)
        assert result == 35
