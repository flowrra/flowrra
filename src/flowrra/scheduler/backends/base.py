"""Base interface for scheduler storage backends."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from flowrra.scheduler.models import ScheduledTask


class BaseSchedulerBackend(ABC):
    """Abstract base class for scheduler storage backends.

    Backends are responsible for persisting scheduled task definitions
    and providing query capabilities for the scheduler service.
    """

    @abstractmethod
    async def create(self, task: ScheduledTask) -> None:
        """Create a new scheduled task.

        Args:
            task: ScheduledTask to store

        Raises:
            ValueError: If task with same ID already exists
        """
        pass

    @abstractmethod
    async def update(self, task: ScheduledTask) -> None:
        """Update an existing scheduled task.

        Args:
            task: ScheduledTask with updated fields

        Raises:
            ValueError: If task doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """Delete a scheduled task.

        Args:
            task_id: ID of task to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def get(self, task_id: str) -> ScheduledTask | None:
        """Get a scheduled task by ID.

        Args:
            task_id: Task ID to retrieve

        Returns:
            ScheduledTask if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_all(self) -> List[ScheduledTask]:
        """List all scheduled tasks.

        Returns:
            List of all ScheduledTask objects
        """
        pass

    @abstractmethod
    async def list_enabled(self) -> List[ScheduledTask]:
        """List only enabled scheduled tasks.

        Returns:
            List of enabled ScheduledTask objects
        """
        pass

    @abstractmethod
    async def list_due(self, now: datetime | None = None) -> List[ScheduledTask]:
        """List tasks that are due for execution.

        Args:
            now: Current time (defaults to datetime.now())

        Returns:
            List of ScheduledTask objects due for execution
        """
        pass

    @abstractmethod
    async def update_run_times(
        self, task_id: str, last_run: datetime, next_run: datetime
    ) -> None:
        """Update task run times after execution.

        Args:
            task_id: ID of the task
            last_run: Timestamp of last execution
            next_run: Timestamp of next scheduled execution

        Raises:
            ValueError: If task doesn't exist
        """
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Clear all scheduled tasks.

        Returns:
            Number of tasks deleted
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close backend connections and cleanup resources."""
        pass
