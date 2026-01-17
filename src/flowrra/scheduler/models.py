"""Scheduler models for persistent task scheduling."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ScheduleType(Enum):
    """Type of schedule for a task."""
    CRON = "cron"
    INTERVAL = "interval"
    ONE_TIME = "one_time"


@dataclass
class ScheduledTask:
    """A task scheduled for execution.

    Attributes:
        id: Unique identifier for scheduled task
        task_name: Name of the registered task to execute
        schedule_type: Type of schedule (cron, interval, one_time)
        schedule: Schedule definition (cron expression or interval in seconds)
        args: Positional arguments for task execution
        kwargs: Keyword arguments for task execution
        enabled: Whether the scheduled task is active
        last_run_at: Timestamp of last execution
        next_run_at: Timestamp of next scheduled execution
        created_at: When the scheduled task was created
        updated_at: When the scheduled task was last updated
        description: Optional description of the task
        max_retries: Maximum retry attempts on failure
        retry_delay: Delay between retries in seconds
        priority: Task priority (higher = more important)
    """

    id: str
    task_name: str
    schedule_type: ScheduleType
    schedule: str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    enabled: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    description: str | None = None
    max_retries: int = 3
    retry_delay: float = 1.0
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "task_name": self.task_name,
            "schedule_type": self.schedule_type.value,
            "schedule": self.schedule,
            "args": list(self.args),
            "kwargs": self.kwargs,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "description": self.description,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduledTask":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            task_name=data["task_name"],
            schedule_type=ScheduleType(data["schedule_type"]),
            schedule=data["schedule"],
            args=tuple(data.get("args", [])),
            kwargs=data.get("kwargs", {}),
            enabled=data.get("enabled", True),
            last_run_at=datetime.fromisoformat(data["last_run_at"]) if data.get("last_run_at") else None,
            next_run_at=datetime.fromisoformat(data["next_run_at"]) if data.get("next_run_at") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            description=data.get("description"),
            max_retries=data.get("max_retries", 3),
            retry_delay=data.get("retry_delay", 1.0),
            priority=data.get("priority", 0),
        )
