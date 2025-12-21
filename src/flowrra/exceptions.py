"""Custom exceptions for flowrra."""

class FlowrraError(Exception):
    pass


class TaskNotFoundError(FlowrraError):
    """Raised when a task is not found in the registry."""

    def __init__(self, task_name: str):
        self.task_name = task_name
        super().__init__(f"Task '{task_name}' not registered")


class TaskTimeoutError(FlowrraError):
    """Raised when waiting for a task result times out."""

    def __init__(self, task_id: int, timeout: float):
        self.task_id = task_id
        self.timeout = timeout
        super().__init__(f"Task '{task_id}' did not complete within {timeout}s")


class ExecutorNotRunningError(FlowrraError):
    """Raised when submitting to a stopped executor."""

    def __init__(self):
        super().__init__("Executor is not running. Call start() first.")


class BackendError(FlowrraError):
    """Raised when a backend operation fails."""
    pass
