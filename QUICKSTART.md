# Flowrra Quick Start Guide

Get started with Flowrra in 5 minutes!

## Installation

```bash
# Install from source (for development)
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"

# When published to PyPI (future):
pip install flowrra
```

## Basic Usage

### 1. Simple Async Task

```python
import asyncio
from flowrra import AsyncTaskExecutor

async def main():
    # Create executor
    executor = AsyncTaskExecutor(num_workers=4)

    # Register a task
    @executor.task()
    async def send_email(to: str, subject: str):
        await asyncio.sleep(1)  # Simulate sending
        return f"Email sent to {to}"

    # Use context manager for automatic cleanup
    async with executor:
        # Submit task
        task_id = await executor.submit(send_email, "user@example.com", "Hello!")

        # Wait for result
        result = await executor.wait_for_result(task_id, timeout=5.0)

        print(f"Status: {result.status.value}")
        print(f"Result: {result.result}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Status: success
Result: Email sent to user@example.com
```

### 2. CPU-Bound Tasks

For compute-heavy work, use `cpu_bound=True`:

```python
import asyncio
from flowrra import AsyncTaskExecutor

async def main():
    executor = AsyncTaskExecutor(num_workers=2, cpu_workers=4)

    # CPU-bound task must be sync (not async)
    @executor.task(cpu_bound=True)
    def compute_fibonacci(n: int):
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    async with executor:
        task_id = await executor.submit(compute_fibonacci, 1000)
        result = await executor.wait_for_result(task_id, timeout=5.0)

        print(f"Fibonacci(1000) calculated: {len(str(result.result))} digits")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Retry Logic

Tasks automatically retry on failure:

```python
import asyncio
import random
from flowrra import AsyncTaskExecutor

async def main():
    executor = AsyncTaskExecutor(num_workers=2)

    @executor.task(max_retries=5, retry_delay=0.5)
    async def flaky_api_call():
        if random.random() < 0.7:  # 70% failure rate
            raise RuntimeError("API temporarily unavailable")
        return {"status": "success"}

    async with executor:
        task_id = await executor.submit(flaky_api_call)
        result = await executor.wait_for_result(task_id, timeout=10.0)

        print(f"Status: {result.status.value}")
        print(f"Retries: {result.retries}")
        print(f"Result: {result.result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Priority Tasks

Higher priority tasks (lower number) execute first:

```python
import asyncio
from flowrra import AsyncTaskExecutor

async def main():
    executor = AsyncTaskExecutor(num_workers=1)  # Single worker

    @executor.task()
    async def process_task(name: str):
        await asyncio.sleep(0.1)
        print(f"Processing: {name}")
        return name

    async with executor:
        # Submit tasks (high priority goes first)
        await executor.submit(process_task, "Low priority", priority=100)
        await executor.submit(process_task, "High priority", priority=1)
        await executor.submit(process_task, "Medium priority", priority=50)

        await asyncio.sleep(1.0)  # Wait for completion

if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Processing: High priority
Processing: Medium priority
Processing: Low priority
```

### 5. Multiple Tasks

Process multiple tasks concurrently:

```python
import asyncio
from flowrra import AsyncTaskExecutor

async def main():
    executor = AsyncTaskExecutor(num_workers=5)

    @executor.task()
    async def fetch_data(url: str):
        await asyncio.sleep(0.5)  # Simulate HTTP request
        return f"Data from {url}"

    async with executor:
        # Submit multiple tasks
        urls = [
            "https://api.example.com/users",
            "https://api.example.com/posts",
            "https://api.example.com/comments",
        ]

        task_ids = []
        for url in urls:
            task_id = await executor.submit(fetch_data, url)
            task_ids.append(task_id)

        # Wait for all results
        results = []
        for task_id in task_ids:
            result = await executor.wait_for_result(task_id, timeout=5.0)
            results.append(result.result)

        print("All data fetched:")
        for data in results:
            print(f"  - {data}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 6. Custom Backend

Use a custom backend for result storage:

```python
import asyncio
from flowrra import AsyncTaskExecutor
from flowrra.backends.memory import InMemoryBackend

async def main():
    # Create custom backend
    backend = InMemoryBackend()

    # Pass to executor
    executor = AsyncTaskExecutor(num_workers=2, backend=backend)

    @executor.task()
    async def my_task(x: int):
        return x * 2

    async with executor:
        task_id = await executor.submit(my_task, 21)
        result = await executor.wait_for_result(task_id, timeout=2.0)

        print(f"Result: {result.result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Concepts

### Task Decorator

```python
@executor.task(
    name=None,           # Custom name (defaults to function name)
    cpu_bound=False,     # True for CPU-intensive work
    max_retries=3,       # Retry attempts on failure
    retry_delay=1.0      # Seconds between retries
)
```

### Task Submission

```python
task_id = await executor.submit(
    task_func,           # The task function
    *args,               # Positional arguments
    priority=0,          # Lower number = higher priority
    **kwargs             # Keyword arguments
)
```

### Task States

- **PENDING**: Queued, not started
- **RUNNING**: Currently executing
- **SUCCESS**: Completed successfully
- **FAILED**: Failed after all retries
- **RETRYING**: Failed, will retry

### Executor Configuration

```python
executor = AsyncTaskExecutor(
    num_workers=4,          # I/O worker coroutines
    cpu_workers=None,       # CPU worker processes (defaults to CPU count)
    max_queue_size=1000,    # Maximum pending tasks
    backend=None            # Result storage backend
)
```

## Common Patterns

### Error Handling

```python
from flowrra import AsyncTaskExecutor
from flowrra.task import TaskStatus

async def main():
    executor = AsyncTaskExecutor(num_workers=2)

    @executor.task(max_retries=2)
    async def risky_task():
        raise ValueError("Something went wrong")

    async with executor:
        task_id = await executor.submit(risky_task)
        result = await executor.wait_for_result(task_id, timeout=5.0)

        if result.status == TaskStatus.FAILED:
            print(f"Task failed: {result.error}")
        else:
            print(f"Task succeeded: {result.result}")
```

### Mixed I/O and CPU Tasks

```python
async def main():
    executor = AsyncTaskExecutor(num_workers=4, cpu_workers=2)

    # I/O-bound (async)
    @executor.task()
    async def fetch_data(url: str):
        await asyncio.sleep(1)
        return f"data from {url}"

    # CPU-bound (sync)
    @executor.task(cpu_bound=True)
    def process_data(data: str):
        return data.upper()

    async with executor:
        # Fetch data (I/O)
        fetch_id = await executor.submit(fetch_data, "api.example.com")
        fetch_result = await executor.wait_for_result(fetch_id)

        # Process data (CPU)
        process_id = await executor.submit(process_data, fetch_result.result)
        process_result = await executor.wait_for_result(process_id)

        print(process_result.result)
```

## Next Steps

- **Read the full docs**: Check out `DEVELOPMENT.md` for detailed info
- **Explore examples**: See `examples/` directory for more patterns
- **Run tests**: Try `pytest tests/ -v` to see the test suite
- **Implement Redis backend**: Extend `BaseResultBackend` for distributed tasks

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Examples**: Check `examples/basic_usage.py`
- **Tests**: Look at `tests/` for usage patterns

Happy tasking! 🚀
