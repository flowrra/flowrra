"""Base broker interface for task queueing."""

from abc import ABC, abstractmethod
from flowrra.task import Task


class BaseBroker(ABC):
    """Abstract base class for task queue brokers.

    Brokers handle task queueing and distribution to workers.
    Unlike backends (which store results), brokers manage the task queue.
    """

    @abstractmethod
    async def push(self, task: Task) -> None:
        """Push a task to the queue.

        Args:
            task: Task to queue
        """
        pass

    @abstractmethod
    async def pop(self, timeout: float | None = None) -> Task | None:
        """Pop a task from the queue.

        Args:
            timeout: Maximum time to wait for a task (None = wait indefinitely)

        Returns:
            Task if available, None if timeout
        """
        pass

    @abstractmethod
    async def size(self) -> int:
        """Get the number of tasks in the queue.

        Returns:
            Number of pending tasks
        """
        pass

    async def close(self) -> None:
        """Close broker connections and cleanup resources.

        Optional method for brokers that need cleanup.
        """
        pass
