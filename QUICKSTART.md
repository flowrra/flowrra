# Flowrra Quick Start Guide

Get started with Flowrra in 5 minutes!

## Installation

```bash
# Install from source (for development)
pip install -e .

# With Redis backend support (recommended for production)
pip install -e ".[redis]"

# Or install with dev dependencies
pip install -e ".[dev]"

# When published to PyPI (future):
pip install flowrra
pip install flowrra[redis]  # With Redis support
```

## Basic Usage

### 1. Simple Async Task

```python
import asyncio
from flowrra import Flowrra

async def main():
    # Create Flowrra application
    app = Flowrra.from_urls()

    # Register an I/O-bound task (async)
    @app.task()
    async def send_email(to: str, subject: str):
        await asyncio.sleep(1)  # Simulate sending
        return f"Email sent to {to}"

    # Use context manager for automatic cleanup
    async with app:
        # Submit task
        task_id = await app.submit(send_email, "user@example.com", "Hello!")

        # Wait for result
        result = await app.wait_for_result(task_id, timeout=5.0)

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

For compute-heavy work, use `cpu_bound=True` with Redis backend:

```python
import asyncio
from flowrra import Flowrra

async def main():
    # CPU tasks require explicit backend for cross-process result sharing
    app = Flowrra.from_urls(
        backend="redis://localhost:6379/0"  # Redis connection string
    )

    # CPU-bound task must be sync (not async)
    @app.task(cpu_bound=True)
    def compute_fibonacci(n: int):
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    async with app:
        task_id = await app.submit(compute_fibonacci, 1000)
        result = await app.wait_for_result(task_id, timeout=5.0)

        print(f"Fibonacci(1000) calculated: {len(str(result.result))} digits")

if __name__ == "__main__":
    asyncio.run(main())
```

**Note:** Requires Redis server running and `pip install flowrra[redis]`

### 3. Retry Logic

Tasks automatically retry on failure:

```python
import asyncio
import random
from flowrra import Flowrra

async def main():
    app = Flowrra.from_urls()

    @app.task(max_retries=5, retry_delay=0.5)
    async def flaky_api_call():
        if random.random() < 0.7:  # 70% failure rate
            raise RuntimeError("API temporarily unavailable")
        return {"status": "success"}

    async with app:
        task_id = await app.submit(flaky_api_call)
        result = await app.wait_for_result(task_id, timeout=10.0)

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
from flowrra import Flowrra

async def main():
    app = Flowrra.from_urls()

    @app.task()
    async def process_task(name: str):
        await asyncio.sleep(0.1)
        print(f"Processing: {name}")
        return name

    async with app:
        # Submit tasks (high priority goes first)
        await app.submit(process_task, "Low priority", priority=100)
        await app.submit(process_task, "High priority", priority=1)
        await app.submit(process_task, "Medium priority", priority=50)

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
from flowrra import Flowrra

async def main():
    app = Flowrra.from_urls()

    @app.task()
    async def fetch_data(url: str):
        await asyncio.sleep(0.5)  # Simulate HTTP request
        return f"Data from {url}"

    async with app:
        # Submit multiple tasks
        urls = [
            "https://api.example.com/users",
            "https://api.example.com/posts",
            "https://api.example.com/comments",
        ]

        task_ids = []
        for url in urls:
            task_id = await app.submit(fetch_data, url)
            task_ids.append(task_id)

        # Wait for all results
        results = []
        for task_id in task_ids:
            result = await app.wait_for_result(task_id, timeout=5.0)
            results.append(result.result)

        print("All data fetched:")
        for data in results:
            print(f"  - {data}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 6. Redis Backend for Production

Use Redis backend and broker for distributed execution:

```python
import asyncio
from flowrra import Flowrra

async def main():
    # Use Redis for both broker and backend (requires Redis server running)
    app = Flowrra.from_urls(
        broker="redis://localhost:6379/0",   # Task queue
        backend="redis://localhost:6379/1"   # Result storage
    )

    @app.task()
    async def my_task(x: int):
        return x * 2

    async with app:
        task_id = await app.submit(my_task, 21)
        result = await app.wait_for_result(task_id, timeout=2.0)

        print(f"Result: {result.result}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Redis Connection String Options:**
- Basic: `redis://localhost:6379/0`
- With password: `redis://:password@localhost:6379/0`
- SSL: `rediss://localhost:6379/0`
- Unix socket: `unix:///tmp/redis.sock`

## Key Concepts

### Flowrra Application

Create a unified application that handles both I/O-bound and CPU-bound tasks:

**Approach 1: Using `from_urls()` (Simple)**

```python
from flowrra import Flowrra

# Simple in-memory configuration
app = Flowrra.from_urls()

# With Redis backend and broker
app = Flowrra.from_urls(
    broker="redis://localhost:6379/0",   # Task queue
    backend="redis://localhost:6379/1"   # Result storage
)
```

**Approach 2: Using `Config` (Advanced)**

```python
from flowrra import Flowrra, Config, BrokerConfig, BackendConfig, ExecutorConfig

# Full configuration with all options
config = Config(
    broker=BrokerConfig(
        url="redis://localhost:6379/0",
        max_connections=50,
        socket_timeout=5.0,
        retry_on_timeout=True
    ),
    backend=BackendConfig(
        url="redis://localhost:6379/1",
        ttl=3600,  # Result expiration in seconds
        max_connections=50,
        socket_timeout=5.0
    ),
    executor=ExecutorConfig(
        num_workers=10,        # Async workers for I/O tasks
        cpu_workers=4,         # Process workers for CPU tasks
        max_queue_size=1000,
        max_retries=3,
        retry_delay=1.0
    )
)

app = Flowrra(config=config)
```

### Task Registration

**I/O-bound tasks (async):**
```python
@app.task(
    name=None,           # Custom name (defaults to function name)
    max_retries=3,       # Retry attempts on failure
    retry_delay=1.0      # Seconds between retries
)
async def my_io_task():  # Must be async
    pass
```

**CPU-bound tasks (sync):**
```python
@app.task(
    cpu_bound=True,      # Run in separate process
    name=None,           # Custom name (defaults to function name)
    max_retries=3,       # Retry attempts on failure
    retry_delay=1.0      # Seconds between retries
)
def my_cpu_task():       # Must be sync (not async)
    pass
```

### Task Submission

```python
task_id = await app.submit(
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

## Common Patterns

### Error Handling

```python
from flowrra import Flowrra
from flowrra.task import TaskStatus

async def main():
    app = Flowrra.from_urls()

    @app.task(max_retries=2)
    async def risky_task():
        raise ValueError("Something went wrong")

    async with app:
        task_id = await app.submit(risky_task)
        result = await app.wait_for_result(task_id, timeout=5.0)

        if result.status == TaskStatus.FAILED:
            print(f"Task failed: {result.error}")
        else:
            print(f"Task succeeded: {result.result}")
```

### Mixed I/O and CPU Tasks

Use a single Flowrra app for both I/O-bound and CPU-bound tasks:

```python
from flowrra import Flowrra

async def main():
    # Single app handles both I/O and CPU tasks
    app = Flowrra.from_urls(backend="redis://localhost:6379/0")

    # I/O-bound (async)
    @app.task()
    async def fetch_data(url: str):
        await asyncio.sleep(1)
        return f"data from {url}"

    # CPU-bound (sync)
    @app.task(cpu_bound=True)
    def process_data(data: str):
        return data.upper()

    async with app:
        # Fetch data (I/O)
        fetch_id = await app.submit(fetch_data, "api.example.com")
        fetch_result = await app.wait_for_result(fetch_id)

        # Process data (CPU)
        process_id = await app.submit(process_data, fetch_result.result)
        process_result = await app.wait_for_result(process_id)

        print(process_result.result)
```

## Next Steps

- **Read the full docs**: Check out `DEVELOPMENT.md` for detailed info
- **Explore examples**: See `examples/` directory for more patterns
- **Run tests**: Try `pytest tests/ -v` to see the test suite
- **Use Redis backend**: Install `pip install flowrra[redis]` for distributed task execution
- **Custom backends**: Extend `BaseResultBackend` for specialized storage needs

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Examples**: Check `examples/basic_usage.py`
- **Tests**: Look at `tests/` for usage patterns

Happy tasking! 🚀
