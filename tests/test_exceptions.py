"""Tests for custom exceptions."""

import pytest
from flowrra.exceptions import (
    FlowrraError,
    TaskNotFoundError,
    TaskTimeoutError,
    ExecutorNotRunningError,
    BackendError,
)


class TestExceptions:
    """Tests for exception classes."""

    def test_flowrra_error_inheritance(self):
        """Test FlowrraError inherits from Exception."""
        assert issubclass(FlowrraError, Exception)

    def test_task_not_found_error(self):
        """Test TaskNotFoundError."""
        error = TaskNotFoundError("my_task")

        assert isinstance(error, FlowrraError)
        assert error.task_name == "my_task"
        assert str(error) == "Task 'my_task' not registered"

    def test_task_timeout_error(self):
        """Test TaskTimeoutError."""
        error = TaskTimeoutError("task-123", 5.0)

        assert isinstance(error, FlowrraError)
        assert error.task_id == "task-123"
        assert error.timeout == 5.0
        assert str(error) == "Task 'task-123' did not complete within 5.0s"

    def test_executor_not_running_error(self):
        """Test ExecutorNotRunningError."""
        error = ExecutorNotRunningError()

        assert isinstance(error, FlowrraError)
        assert str(error) == "Executor is not running. Call start() first."

    def test_backend_error(self):
        """Test BackendError."""
        error = BackendError("Connection failed")

        assert isinstance(error, FlowrraError)
        assert str(error) == "Connection failed"
