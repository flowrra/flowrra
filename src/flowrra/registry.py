import asyncio
from typing import Callable, Coroutine, Any

from flowrra.exceptions import TaskNotFoundError


class TaskRegistry:
    def __init__(self, strict_cpu_checks: bool = True):
        """Initialize the task registry.

        Args:
            strict_cpu_checks: If True, enforce module-level requirement for CPU tasks.
                              Set to False for testing purposes only.
        """
        self._tasks: dict[str, Callable[..., Any]] = {}
        self._strict_cpu_checks = strict_cpu_checks

    def task(
        self,
        name: str | None = None,
        cpu_bound: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """Decorator to register an async function as a task.

        Args:
            name: Custom task name (defaults to function name)
            cpu_bound: Whether task is CPU-bound (runs in ProcessPoolExecutor)
            max_retries: Max retry attempts on failure
            retry_delay: Seconds between retries
        """
        def decorator(func: Callable[..., Coroutine]):
            task_name = name or func.__name__
            if cpu_bound:
                if asyncio.iscoroutinefunction(func):
                    raise TypeError(
                        f"CPU-bound task '{task_name}' must be a sync function, not async"
                    )

                if self._strict_cpu_checks and func.__qualname__ != func.__name__:
                    raise TypeError(
                        f"CPU-bound task '{task_name}' must be module-level"
                    )
            else:
                if not asyncio.iscoroutinefunction(func):
                    raise TypeError(
                        f"Task '{task_name}' must be an async function."
                    )
                
            if task_name in self._tasks:
                raise ValueError(f"Task '{task_name}' is already registered")
            
            func.task_name = task_name
            func.cpu_bound = cpu_bound
            func.max_retries = max_retries
            func.retry_delay = retry_delay
            func.__flowrra_task__ = True
            self._tasks[task_name] = func
            return func
        
        return decorator
    
    def get(self, name: str):
        return self._tasks.get(name)
    
    def get_or_raise(self, name: str):
        task = self._tasks.get(name)
        if task is None:
            raise TaskNotFoundError(name)
        
        return task
    
    def list_tasks(self):
        return list(self._tasks.keys())

    def is_registered(self, name: str):
        return name in self._tasks
    
    def unregister(self, name):
        if name in self._tasks:
            del self._tasks[name]
            return True
        
        return False
    
    def __len__(self):
        return len(self._tasks)

    def __contains__(self, name):
        return name in self._tasks
    