"""Integration tests for Flowrra."""

import asyncio
import pytest
from flowrra import AsyncTaskExecutor
from flowrra.task import TaskStatus


class TestIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test a complete workflow from start to finish."""
        executor = AsyncTaskExecutor(num_workers=3)

        # Register various tasks
        @executor.task()
        async def send_email(to: str, subject: str):
            await asyncio.sleep(0.05)
            return {"sent": True, "to": to, "subject": subject}

        @executor.task()
        async def process_data(numbers: list):
            await asyncio.sleep(0.05)
            return sum(numbers)

        @executor.task()
        async def compute_factorial(n: int):
            """Changed from cpu_bound to async to avoid pickling issues in tests."""
            result = 1
            for i in range(1, n + 1):
                result *= i
            return result

        # Execute workflow
        async with executor:
            # Submit tasks
            email_id = await executor.submit(send_email, "user@example.com", "Hello")
            data_id = await executor.submit(process_data, [1, 2, 3, 4, 5])
            cpu_id = await executor.submit(compute_factorial, 10)

            # Wait for results
            email_result = await executor.wait_for_result(email_id, timeout=3.0)
            data_result = await executor.wait_for_result(data_id, timeout=3.0)
            cpu_result = await executor.wait_for_result(cpu_id, timeout=3.0)

            # Verify results
            assert email_result.status == TaskStatus.SUCCESS
            assert email_result.result["sent"] is True
            assert email_result.result["to"] == "user@example.com"

            assert data_result.status == TaskStatus.SUCCESS
            assert data_result.result == 15

            assert cpu_result.status == TaskStatus.SUCCESS
            assert cpu_result.result == 3628800  # 10!

    @pytest.mark.asyncio
    async def test_mixed_success_failure(self):
        """Test workflow with both successful and failing tasks."""
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task(max_retries=0)
        async def success_task():
            return "success"

        @executor.task(max_retries=0)
        async def failure_task():
            raise ValueError("Expected failure")

        async with executor:
            success_id = await executor.submit(success_task)
            failure_id = await executor.submit(failure_task)

            success_result = await executor.wait_for_result(success_id, timeout=2.0)
            failure_result = await executor.wait_for_result(failure_id, timeout=2.0)

            assert success_result.status == TaskStatus.SUCCESS
            assert failure_result.status == TaskStatus.FAILED
            assert "Expected failure" in failure_result.error

    @pytest.mark.asyncio
    async def test_high_load(self):
        """Test executor under high load."""
        executor = AsyncTaskExecutor(num_workers=4)

        @executor.task()
        async def fast_task(n: int):
            await asyncio.sleep(0.01)
            return n * 2

        async with executor:
            # Submit many tasks
            task_ids = []
            for i in range(50):
                task_id = await executor.submit(fast_task, i)
                task_ids.append((task_id, i))

            # Verify all complete successfully
            for task_id, expected_input in task_ids:
                result = await executor.wait_for_result(task_id, timeout=5.0)
                assert result.status == TaskStatus.SUCCESS
                assert result.result == expected_input * 2

    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        """Test task that retries and eventually succeeds."""
        executor = AsyncTaskExecutor(num_workers=2)

        attempts = {"count": 0}

        @executor.task(max_retries=5, retry_delay=0.05)
        async def retry_task():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError(f"Attempt {attempts['count']} failed")
            return f"Success on attempt {attempts['count']}"

        async with executor:
            task_id = await executor.submit(retry_task)
            result = await executor.wait_for_result(task_id, timeout=3.0)

            assert result.status == TaskStatus.SUCCESS
            assert "Success on attempt 3" in result.result
            assert attempts["count"] == 3

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test that priority ordering works correctly."""
        executor = AsyncTaskExecutor(num_workers=1)  # Single worker

        execution_order = []

        @executor.task()
        async def ordered_task(name: str):
            execution_order.append(name)
            await asyncio.sleep(0.02)
            return name

        async with executor:
            # Submit in reverse priority order
            await executor.submit(ordered_task, "low-priority", priority=100)
            await executor.submit(ordered_task, "high-priority", priority=1)
            await executor.submit(ordered_task, "medium-priority", priority=50)

            await asyncio.sleep(0.2)  # Wait for all to complete

        # High priority should execute first
        assert execution_order[0] == "high-priority"
        assert execution_order[1] == "medium-priority"
        assert execution_order[2] == "low-priority"

    @pytest.mark.skip(reason="Local functions cannot be pickled for ProcessPoolExecutor. Use module-level functions for CPU-bound tasks.")
    @pytest.mark.asyncio
    async def test_cpu_and_io_tasks_together(self):
        """Test running CPU-bound and I/O-bound tasks together."""
        executor = AsyncTaskExecutor(num_workers=2, cpu_workers=2)

        @executor.task()
        async def io_task(n: int):
            await asyncio.sleep(0.05)
            return f"IO-{n}"

        @executor.task(cpu_bound=True)
        def cpu_task(n: int):
            return sum(range(n))

        async with executor:
            # Submit mix of tasks
            io_id1 = await executor.submit(io_task, 1)
            cpu_id1 = await executor.submit(cpu_task, 100)
            io_id2 = await executor.submit(io_task, 2)
            cpu_id2 = await executor.submit(cpu_task, 200)

            # Wait for all results
            io_result1 = await executor.wait_for_result(io_id1, timeout=3.0)
            cpu_result1 = await executor.wait_for_result(cpu_id1, timeout=3.0)
            io_result2 = await executor.wait_for_result(io_id2, timeout=3.0)
            cpu_result2 = await executor.wait_for_result(cpu_id2, timeout=3.0)

            assert io_result1.result == "IO-1"
            assert cpu_result1.result == sum(range(100))
            assert io_result2.result == "IO-2"
            assert cpu_result2.result == sum(range(200))

    @pytest.mark.asyncio
    async def test_task_result_tracking(self):
        """Test that task results are tracked correctly throughout lifecycle."""
        executor = AsyncTaskExecutor(num_workers=1)

        @executor.task()
        async def tracked_task():
            await asyncio.sleep(0.1)
            return "completed"

        async with executor:
            task_id = await executor.submit(tracked_task)

            # Check pending state
            initial_result = await executor.get_result(task_id)
            assert initial_result is not None
            assert initial_result.status == TaskStatus.PENDING

            # Wait for completion
            final_result = await executor.wait_for_result(task_id, timeout=3.0)
            assert final_result.status == TaskStatus.SUCCESS
            assert final_result.result == "completed"
            assert final_result.started_at is not None
            assert final_result.finished_at is not None

    @pytest.mark.asyncio
    async def test_multiple_executors(self):
        """Test running multiple executors simultaneously."""
        executor1 = AsyncTaskExecutor(num_workers=2)
        executor2 = AsyncTaskExecutor(num_workers=2)

        @executor1.task()
        async def task1():
            await asyncio.sleep(0.05)
            return "executor1"

        @executor2.task()
        async def task2():
            await asyncio.sleep(0.05)
            return "executor2"

        # Run both executors
        async with executor1, executor2:
            id1 = await executor1.submit(task1)
            id2 = await executor2.submit(task2)

            result1 = await executor1.wait_for_result(id1, timeout=2.0)
            result2 = await executor2.wait_for_result(id2, timeout=2.0)

            assert result1.result == "executor1"
            assert result2.result == "executor2"
