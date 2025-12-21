"""Tests for task models."""

import pytest
from datetime import datetime
from flowrra.task import Task, TaskResult, TaskStatus


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.SUCCESS.value == "success"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.RETRYING.value == "retrying"


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_task_result_creation(self):
        """Test creating a TaskResult."""
        result = TaskResult(
            task_id="test-123",
            status=TaskStatus.PENDING,
            result=None,
        )

        assert result.task_id == "test-123"
        assert result.status == TaskStatus.PENDING
        assert result.result is None
        assert result.error is None
        assert result.retries == 0

    def test_task_result_with_all_fields(self):
        """Test TaskResult with all fields populated."""
        now = datetime.now()
        result = TaskResult(
            task_id="test-456",
            status=TaskStatus.SUCCESS,
            result={"data": "value"},
            error=None,
            started_at=now,
            finished_at=now,
            retries=2,
        )

        assert result.task_id == "test-456"
        assert result.status == TaskStatus.SUCCESS
        assert result.result == {"data": "value"}
        assert result.retries == 2
        assert result.started_at == now
        assert result.finished_at == now

    def test_is_complete_property(self):
        """Test is_complete property."""
        success_result = TaskResult(
            task_id="test-1",
            status=TaskStatus.SUCCESS,
            result=None,
        )
        assert success_result.is_complete is True

        failed_result = TaskResult(
            task_id="test-2",
            status=TaskStatus.FAILED,
            result=None,
        )
        assert failed_result.is_complete is True

        pending_result = TaskResult(
            task_id="test-3",
            status=TaskStatus.PENDING,
            result=None,
        )
        assert pending_result.is_complete is False

        running_result = TaskResult(
            task_id="test-4",
            status=TaskStatus.RUNNING,
            result=None,
        )
        assert running_result.is_complete is False

    def test_is_success_property(self):
        """Test is_success property."""
        success_result = TaskResult(
            task_id="test-1",
            status=TaskStatus.SUCCESS,
            result=None,
        )
        assert success_result.is_success is True

        failed_result = TaskResult(
            task_id="test-2",
            status=TaskStatus.FAILED,
            result=None,
        )
        assert failed_result.is_success is False

    def test_to_dict(self):
        """Test to_dict serialization."""
        now = datetime.now()
        result = TaskResult(
            task_id="test-789",
            status=TaskStatus.SUCCESS,
            result=42,
            error=None,
            started_at=now,
            finished_at=now,
            retries=1,
        )

        data = result.to_dict

        assert data["task_id"] == "test-789"
        assert data["status"] == "success"
        assert data["result"] == 42
        assert data["error"] is None
        assert data["retries"] == 1
        assert data["started_at"] == now.isoformat()
        assert data["finished_at"] == now.isoformat()

    def test_from_dict(self):
        """Test from_dict deserialization."""
        now = datetime.now()
        data = {
            "task_id": "test-abc",
            "status": "success",
            "result": "hello",
            "error": None,
            "started_at": now.isoformat(),
            "finished_at": now.isoformat(),
            "retries": 0,
        }

        result = TaskResult.from_dict(data)

        assert result.task_id == "test-abc"
        assert result.status == TaskStatus.SUCCESS
        assert result.result == "hello"
        assert result.error is None
        assert result.retries == 0


class TestTask:
    """Tests for Task dataclass."""

    def test_task_creation(self):
        """Test creating a Task."""
        task = Task(
            id="task-123",
            name="my_task",
            args=(1, 2),
            kwargs={"x": 10},
        )

        assert task.id == "task-123"
        assert task.name == "my_task"
        assert task.args == (1, 2)
        assert task.kwargs == {"x": 10}
        assert task.max_retries == 3
        assert task.retry_delay == 1.0
        assert task.current_retry == 0
        assert task.priority == 0

    def test_task_with_custom_values(self):
        """Test Task with custom retry and priority values."""
        task = Task(
            id="task-456",
            name="important_task",
            args=(),
            kwargs={},
            max_retries=5,
            retry_delay=2.5,
            priority=10,
        )

        assert task.max_retries == 5
        assert task.retry_delay == 2.5
        assert task.priority == 10

    def test_task_priority_comparison(self):
        """Test task priority comparison for queue ordering."""
        high_priority = Task(
            id="task-1",
            name="high",
            args=(),
            kwargs={},
            priority=1,
        )

        low_priority = Task(
            id="task-2",
            name="low",
            args=(),
            kwargs={},
            priority=10,
        )

        # Lower number = higher priority
        assert high_priority < low_priority
        assert not (low_priority < high_priority)
