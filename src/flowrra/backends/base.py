from abc import ABC, abstractmethod

from flowrra.task import TaskResult, TaskStatus

class BaseResultBackend(ABC):
    """Abstract base for result storage backends.
    
    Implementations must provide:
    - store(): Persist a task result
    - get(): Retrieve a task result by ID
    - wait_for(): Block until a task completes
    """

    @abstractmethod
    async def store(self, task_id: str, result: TaskResult) -> None:
        """Store a task result.
        
        Args:
            task_id: Unique task identifier
            result: TaskResult object to store
        """
        pass

    @abstractmethod
    async def get(self, task_id: str) -> TaskResult | None:
        """Retrieve a task result.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            TaskResult if found, None otherwise
        """
        pass

    @abstractmethod
    async def wait_for(self, task_id: str, timeout: float | None) -> TaskResult:
        """Wait for a task to complete.
        
        Args:
            task_id: Unique task identifier
            timeout: Maximum seconds to wait (None = wait forever)
            
        Returns:
            TaskResult when task completes
            
        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        pass

    async def delete(self, task_id: str) -> bool:
        """Delete a task result. Optional to implement.
        
        Returns:
            True if deleted, False if not found
        """
        raise NotImplementedError("delete() not supported by this backend")

    async def clear(self) -> int:
        """Clear all results. Optional to implement.

        Returns:
            Number of results cleared
        """
        raise NotImplementedError("clear() not supported by this backend")

    async def list_by_status(
        self,
        status: TaskStatus,
        limit: int | None = None,
        offset: int = 0
    ) -> list[TaskResult]:
        """List tasks by status with optional pagination.

        Optional to implement. Backends that don't support querying should
        raise NotImplementedError (default behavior).

        Args:
            status: Task status to filter by (PENDING, RUNNING, SUCCESS, FAILED, RETRYING)
            limit: Maximum number of results to return (None = no limit)
            offset: Number of results to skip (for pagination)

        Returns:
            List of TaskResult objects matching the status, ordered by submitted_at DESC
            (most recent first). Empty list if no matches found.

        Raises:
            NotImplementedError: If backend doesn't support status queries

        Note:
            - Results are ordered by submitted_at DESC (newest first)
            - If submitted_at is None, those tasks are ordered last
            - InMemoryBackend and RedisBackend both support this operation
        """
        raise NotImplementedError(
            f"list_by_status() not supported by {self.__class__.__name__}"
        )
