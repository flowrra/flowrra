"""Tests for AsyncTaskExecutor."""

import asyncio
import pytest
from flowrra import AsyncTaskExecutor
from flowrra.task import TaskStatus
from flowrra.exceptions import ExecutorNotRunningError, TaskNotFoundError
from flowrra.backends.memory import InMemoryBackend


class TestExecutorInitialization:
    """Tests for executor initialization."""

    def test_executor_creation(self):
        """Test creating an executor."""
        executor = AsyncTaskExecutor(num_workers=4)

        assert executor._num_workers == 4
        assert executor.is_running is False
        assert len(executor.registry) == 0

    def test_executor_with_custom_backend(self):
        """Test executor with custom backend."""
        backend = InMemoryBackend()
        executor = AsyncTaskExecutor(backend=backend)

        assert executor.results is backend

    def test_executor_with_cpu_workers(self):
        """Test executor with CPU workers configured."""
        executor = AsyncTaskExecutor(num_workers=2, cpu_workers=4)

        assert executor._num_workers == 2
        assert executor._cpu_workers == 4


class TestExecutorLifecycle:
    """Tests for executor start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_executor(self):
        """Test starting the executor."""
        executor = AsyncTaskExecutor(num_workers=2)

        assert executor.is_running is False

        await executor.start()

        assert executor.is_running is True
        assert len(executor._workers) == 2

        await executor.stop()

    @pytest.mark.asyncio
    async def test_stop_executor(self):
        """Test stopping the executor."""
        executor = AsyncTaskExecutor(num_workers=2)

        await executor.start()
        assert executor.is_running is True

        await executor.stop()

        assert executor.is_running is False
        assert len(executor._workers) == 0

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test starting an already running executor."""
        executor = AsyncTaskExecutor(num_workers=2)

        await executor.start()
        await executor.start()  # Should be idempotent

        assert executor.is_running is True

        await executor.stop()

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stopping an executor that's not running."""
        executor = AsyncTaskExecutor(num_workers=2)

        await executor.stop()  # Should be idempotent

        assert executor.is_running is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using executor as context manager."""
        executor = AsyncTaskExecutor(num_workers=2)

        assert executor.is_running is False

        async with executor:
            assert executor.is_running is True

        assert executor.is_running is False


class TestTaskSubmission:
    """Tests for submitting tasks."""

    @pytest.mark.asyncio
    async def test_submit_task(self):
        """Test submitting a task."""
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task()
        async def my_task(x: int) -> int:
            return x * 2

        async with executor:
            task_id = await executor.submit(my_task, 10)

            assert isinstance(task_id, str)
            assert len(task_id) > 0

    @pytest.mark.asyncio
    async def test_submit_without_start(self):
        """Test submitting a task before starting executor."""
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task()
        async def my_task():
            return "hello"

        with pytest.raises(ExecutorNotRunningError):
            await executor.submit(my_task)

    @pytest.mark.asyncio
    async def test_submit_unregistered_task(self):
        """Test submitting an unregistered task."""
        executor = AsyncTaskExecutor(num_workers=2)

        async def unregistered():
            return "test"

        unregistered.task_name = "unregistered"

        async with executor:
            with pytest.raises(TaskNotFoundError):
                await executor.submit(unregistered)

    @pytest.mark.asyncio
    async def test_submit_with_args_kwargs(self):
        """Test submitting a task with arguments."""
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task()
        async def add(a: int, b: int, multiplier: int = 1) -> int:
            return (a + b) * multiplier

        async with executor:
            task_id = await executor.submit(add, 10, 20, multiplier=2)

            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == 60

    @pytest.mark.asyncio
    async def test_submit_with_priority(self):
        """Test submitting tasks with different priorities."""
        executor = AsyncTaskExecutor(num_workers=1)  # Single worker to control order

        results_list = []

        @executor.task()
        async def record_task(name: str):
            results_list.append(name)
            await asyncio.sleep(0.01)
            return name

        async with executor:
            # Submit low priority first, then high priority
            await executor.submit(record_task, "low", priority=10)
            await executor.submit(record_task, "high", priority=1)

            await asyncio.sleep(0.1)  # Wait for tasks to complete

        # High priority should run first
        assert results_list[0] == "high"
        assert results_list[1] == "low"


class TestTaskExecution:
    """Tests for task execution."""

    @pytest.mark.asyncio
    async def test_simple_task_execution(self):
        """Test executing a simple task."""
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task()
        async def simple_task():
            return "success"

        async with executor:
            task_id = await executor.submit(simple_task)
            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == "success"
            assert result.error is None

    @pytest.mark.asyncio
    async def test_task_with_sleep(self):
        """Test executing a task with async sleep."""
        executor = AsyncTaskExecutor(num_workers=2)

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
    async def test_multiple_concurrent_tasks(self):
        """Test executing multiple tasks concurrently."""
        executor = AsyncTaskExecutor(num_workers=4)

        @executor.task()
        async def concurrent_task(n: int):
            await asyncio.sleep(0.05)
            return n * 2

        async with executor:
            task_ids = []
            for i in range(10):
                task_id = await executor.submit(concurrent_task, i)
                task_ids.append(task_id)

            # Wait for all results
            results = []
            for task_id in task_ids:
                result = await executor.wait_for_result(task_id, timeout=3.0)
                results.append(result.result)

            assert sorted(results) == [i * 2 for i in range(10)]


class TestTaskRetry:
    """Tests for task retry logic."""

    @pytest.mark.asyncio
    async def test_task_retry_success(self):
        """Test task that fails then succeeds on retry."""
        executor = AsyncTaskExecutor(num_workers=2)

        attempt_count = {"count": 0}

        @executor.task(max_retries=3, retry_delay=0.1)
        async def flaky_task():
            attempt_count["count"] += 1
            if attempt_count["count"] < 3:
                raise RuntimeError("Temporary failure")
            return "success"

        async with executor:
            task_id = await executor.submit(flaky_task)
            result = await executor.wait_for_result(task_id, timeout=3.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == "success"
            assert result.retries >= 2

    @pytest.mark.asyncio
    async def test_task_retry_exhausted(self):
        """Test task that exhausts all retries."""
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task(max_retries=2, retry_delay=0.05)
        async def always_fails():
            raise ValueError("Always fails")

        async with executor:
            task_id = await executor.submit(always_fails)
            result = await executor.wait_for_result(task_id, timeout=3.0)

            assert result.status == TaskStatus.FAILED
            assert "Always fails" in result.error
            assert result.retries == 2


class TestCPUBoundTasks:
    """Tests for CPU-bound task execution."""

    @pytest.mark.skip(reason="Local functions cannot be pickled for ProcessPoolExecutor. Use module-level functions for CPU-bound tasks.")
    @pytest.mark.asyncio
    async def test_cpu_bound_task(self):
        """Test executing a CPU-bound task."""
        executor = AsyncTaskExecutor(num_workers=2, cpu_workers=2)

        @executor.task(cpu_bound=True)
        def compute_sum(n: int):
            return sum(range(n))

        async with executor:
            task_id = await executor.submit(compute_sum, 1000)
            result = await executor.wait_for_result(task_id, timeout=3.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == sum(range(1000))

    @pytest.mark.skip(reason="Local functions cannot be pickled for ProcessPoolExecutor. Use module-level functions for CPU-bound tasks.")
    @pytest.mark.asyncio
    async def test_cpu_bound_with_args(self):
        """Test CPU-bound task with multiple arguments."""
        executor = AsyncTaskExecutor(num_workers=2, cpu_workers=2)

        @executor.task(cpu_bound=True)
        def multiply(a: int, b: int):
            return a * b

        async with executor:
            task_id = await executor.submit(multiply, 123, 456)
            result = await executor.wait_for_result(task_id, timeout=3.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == 123 * 456


class TestResultRetrieval:
    """Tests for result retrieval."""

    @pytest.mark.asyncio
    async def test_get_result(self):
        """Test getting a result immediately."""
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task()
        async def my_task():
            return 42

        async with executor:
            task_id = await executor.submit(my_task)
            await asyncio.sleep(0.2)  # Let task complete

            result = await executor.get_result(task_id)

            assert result is not None
            assert result.status == TaskStatus.SUCCESS
            assert result.result == 42

    @pytest.mark.asyncio
    async def test_wait_for_result_timeout(self):
        """Test wait_for_result with timeout."""
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task()
        async def slow_task():
            await asyncio.sleep(10)  # Very slow
            return "done"

        async with executor:
            task_id = await executor.submit(slow_task)

            with pytest.raises(asyncio.TimeoutError):
                await executor.wait_for_result(task_id, timeout=0.1)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_task_with_exception(self):
        """Test task that raises an exception."""
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task(max_retries=0)
        async def failing_task():
            raise ValueError("Test error")

        async with executor:
            task_id = await executor.submit(failing_task)
            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.FAILED
            assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_pending_tasks(self):
        """Test graceful shutdown waits for pending tasks."""
        executor = AsyncTaskExecutor(num_workers=1)

        completed = []

        @executor.task()
        async def slow_task(n: int):
            await asyncio.sleep(0.1)
            completed.append(n)
            return n

        await executor.start()

        # Submit multiple tasks
        for i in range(3):
            await executor.submit(slow_task, i)

        # Stop with wait=True
        await executor.stop(wait=True, timeout=5.0)

        # All tasks should complete
        assert len(completed) == 3

    @pytest.mark.asyncio
    async def test_empty_queue(self):
        """Test executor with no tasks."""
        executor = AsyncTaskExecutor(num_workers=2)

        async with executor:
            await asyncio.sleep(0.1)  # Just run briefly

        # Should exit cleanly with no tasks

    @pytest.mark.asyncio
    async def test_pending_count(self):
        """Test pending_count property."""
        executor = AsyncTaskExecutor(num_workers=1)

        @executor.task()
        async def slow_task():
            await asyncio.sleep(1.0)
            return "done"

        async with executor:
            # Queue size should be accessible
            initial_count = executor.pending_count
            assert initial_count >= 0
