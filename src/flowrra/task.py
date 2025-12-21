from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    retries: int = 0

    @property
    def is_complete(self) -> bool:
        return self.status in (TaskStatus.SUCCESS, TaskStatus.FAILED)
    
    @property
    def is_success(self) -> bool:
        return self.status == TaskStatus.SUCCESS
    
    @property
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "retries": self.retries,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TaskResult":
        return cls(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            result=data["result"],
            error=data["error"],
            started_at=datetime.fromisoformat(data["started_at"]) if data["started_at"] else None,
            finished_at=datetime.fromisoformat(data["finished_at"]) if data["finished_at"] else None,
            retries=data["retries"],
        )
    
@dataclass
class Task:
    id: str
    name: str
    args: tuple
    kwargs: dict
    max_retries: int = 3
    retry_delay: float = 1.0
    current_retry: int = 0
    priority: int = 0

    def __lt__(self, other):
        return self.priority < other.priority
