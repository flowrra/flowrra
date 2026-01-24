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
    task_name: str | None = None
    result: Any = None
    error: str | None = None
    submitted_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    retries: int = 0
    args: tuple = ()
    kwargs: dict = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}

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
            "task_name": self.task_name,
            "result": self.result,
            "error": self.error,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "retries": self.retries,
            "args": self.args,
            "kwargs": self.kwargs,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TaskResult":
        return cls(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            task_name=data.get("task_name"),
            result=data.get("result"),
            error=data.get("error"),
            submitted_at=datetime.fromisoformat(data["submitted_at"]) if data.get("submitted_at") else None,
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            finished_at=datetime.fromisoformat(data["finished_at"]) if data.get("finished_at") else None,
            retries=data.get("retries", 0),
            args=tuple(data.get("args", ())),
            kwargs=data.get("kwargs", {}),
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
    cpu_bound: bool = False

    def __lt__(self, other):
        return self.priority < other.priority
