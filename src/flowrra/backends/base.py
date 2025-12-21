from abc import ABC, abstractmethod

from flowrra.task import TaskResult

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