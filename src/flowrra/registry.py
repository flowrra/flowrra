import asyncio
from functools import wraps
from typing import Callable, Coroutine

from flowrra.exceptions import TaskNotFoundError


class TaskRegistry:
    def __init__(self):
        self._tasks: dict[str, Callable[..., Coroutine]] = {}
    
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
                
                func.task_name = task_name
                func.cpu_bound = cpu_bound
                func.max_retries = max_retries
                func.retry_delay = retry_delay
                func.is_flowrra_task = True
                self._tasks[task_name] = func
                return func
            else:
                if not asyncio.iscoroutinefunction(func):
                    raise TypeError(
                        f"Task '{task_name}' must be an async function."
                    )

                @wraps(func)
                async def wrapper(*args, **kwargs):
                    return await func(*args, **kwargs)
                
                wrapper.task_name = task_name
                wrapper.cpu_bound = cpu_bound
                wrapper.max_retries = max_retries
                wrapper.retry_delay = retry_delay
                wrapper.is_flowrra_task = True

                self._tasks[task_name] = wrapper

                return wrapper
        
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
    