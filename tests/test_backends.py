"""Tests for result backends."""

import asyncio
import pytest
from flowrra.backends.memory import InMemoryBackend
from flowrra.task import TaskResult, TaskStatus


class TestInMemoryBackend:
    """Tests for InMemoryBackend."""

    @pytest.mark.asyncio
    async def test_backend_initialization(self):
        """Test backend initializes empty."""
        backend = InMemoryBackend()
        assert len(backend) == 0

    @pytest.mark.asyncio
    async def test_store_and_get(self):
        """Test storing and retrieving a task result."""
        backend = InMemoryBackend()
        result = TaskResult(
            task_id="task-123",
            status=TaskStatus.SUCCESS,
            result=42,
        )

        await backend.store("task-123", result)

        retrieved = await backend.get("task-123")
        assert retrieved is not None
        assert retrieved.task_id == "task-123"
        assert retrieved.status == TaskStatus.SUCCESS
        assert retrieved.result == 42

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self):
        """Test getting a result that doesn't exist."""
        backend = InMemoryBackend()

        result = await backend.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_result(self):
        """Test updating an existing result."""
        backend = InMemoryBackend()

        # Store initial result
        result1 = TaskResult(
            task_id="task-456",
            status=TaskStatus.PENDING,
            result=None,
        )
        await backend.store("task-456", result1)

        # Update to running
        result2 = TaskResult(
            task_id="task-456",
            status=TaskStatus.RUNNING,
            result=None,
        )
        await backend.store("task-456", result2)

        # Update to success
        result3 = TaskResult(
            task_id="task-456",
            status=TaskStatus.SUCCESS,
            result="done",
        )
        await backend.store("task-456", result3)

        # Verify final state
        retrieved = await backend.get("task-456")
        assert retrieved.status == TaskStatus.SUCCESS
        assert retrieved.result == "done"

    @pytest.mark.asyncio
    async def test_wait_for_completed_task(self):
        """Test wait_for when task is already complete."""
        backend = InMemoryBackend()

        result = TaskResult(
            task_id="task-789",
            status=TaskStatus.SUCCESS,
            result="completed",
        )
        await backend.store("task-789", result)

        # Should return immediately since task is complete
        retrieved = await backend.wait_for("task-789", timeout=1.0)
        assert retrieved.task_id == "task-789"
        assert retrieved.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_wait_for_task_that_completes(self):
        """Test wait_for a task that completes while waiting."""
        backend = InMemoryBackend()

        # Store pending result
        pending = TaskResult(
            task_id="task-abc",
            status=TaskStatus.PENDING,
            result=None,
        )
        await backend.store("task-abc", pending)

        async def complete_task():
            """Complete the task after a short delay."""
            await asyncio.sleep(0.1)
            success = TaskResult(
                task_id="task-abc",
                status=TaskStatus.SUCCESS,
                result="finished",
            )
            await backend.store("task-abc", success)

        # Start completion task
        complete_task_coro = asyncio.create_task(complete_task())

        # Wait for result
        result = await backend.wait_for("task-abc", timeout=2.0)

        await complete_task_coro

        assert result.status == TaskStatus.SUCCESS
        assert result.result == "finished"

    @pytest.mark.asyncio
    async def test_wait_for_timeout(self):
        """Test wait_for times out if task doesn't complete."""
        backend = InMemoryBackend()

        # Store pending result that never completes
        pending = TaskResult(
            task_id="task-timeout",
            status=TaskStatus.PENDING,
            result=None,
        )
        await backend.store("task-timeout", pending)

        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await backend.wait_for("task-timeout", timeout=0.1)

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Test deleting a task result."""
        backend = InMemoryBackend()

        result = TaskResult(
            task_id="task-delete",
            status=TaskStatus.SUCCESS,
            result="data",
        )
        await backend.store("task-delete", result)
        assert len(backend) == 1

        deleted = await backend.delete("task-delete")
        assert deleted is True
        assert len(backend) == 0

        retrieved = await backend.get("task-delete")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self):
        """Test deleting a task that doesn't exist."""
        backend = InMemoryBackend()

        deleted = await backend.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear_backend(self):
        """Test clearing all results."""
        backend = InMemoryBackend()

        # Store multiple results
        for i in range(5):
            result = TaskResult(
                task_id=f"task-{i}",
                status=TaskStatus.SUCCESS,
                result=i,
            )
            await backend.store(f"task-{i}", result)

        assert len(backend) == 5

        # Clear all
        count = await backend.clear()
        assert count == 5
        assert len(backend) == 0

        # Verify all tasks are gone
        for i in range(5):
            retrieved = await backend.get(f"task-{i}")
            assert retrieved is None

    @pytest.mark.asyncio
    async def test_multiple_waiters(self):
        """Test multiple coroutines waiting for the same task."""
        backend = InMemoryBackend()

        # Store pending result
        pending = TaskResult(
            task_id="task-multi",
            status=TaskStatus.PENDING,
            result=None,
        )
        await backend.store("task-multi", pending)

        async def complete_task():
            """Complete the task after a short delay."""
            await asyncio.sleep(0.1)
            success = TaskResult(
                task_id="task-multi",
                status=TaskStatus.SUCCESS,
                result="done",
            )
            await backend.store("task-multi", success)

        # Start multiple waiters
        waiter1 = asyncio.create_task(backend.wait_for("task-multi", timeout=2.0))
        waiter2 = asyncio.create_task(backend.wait_for("task-multi", timeout=2.0))
        waiter3 = asyncio.create_task(backend.wait_for("task-multi", timeout=2.0))

        # Complete the task
        completer = asyncio.create_task(complete_task())

        # All waiters should get the result
        results = await asyncio.gather(waiter1, waiter2, waiter3, completer)

        for result in results[:3]:  # First 3 are waiters
            assert result.status == TaskStatus.SUCCESS
            assert result.result == "done"
