# Flowrra

Lightweight async task queue built on pure Python asyncio. A Celery-inspired background job executor with zero dependencies, featuring retries, priority queues, and pluggable backends.

## Features

- **Zero Dependencies** - Built on pure Python 3.11+ asyncio
- **Simple API** - Decorator-based task registration, just like Celery
- **Async First** - Native async/await support for I/O-bound tasks
- **CPU-Bound Support** - ProcessPoolExecutor integration for compute-heavy tasks
- **Automatic Retries** - Configurable retry logic with exponential backoff
- **Priority Queues** - Control task execution order
- **Pluggable Backends** - Extensible result storage (in-memory included)
- **Type Safe** - Full type hints for better IDE support

## Installation

```bash
pip install flowrra
```

For development:
```bash
pip install flowrra[dev]
```

## Quick Start

```python
import asyncio
from flowrra import AsyncTaskExecutor

# Create executor
executor = AsyncTaskExecutor(num_workers=4)

# Register tasks
@executor.task()
async def send_email(to: str, subject: str, body: str):
    """Send an email asynchronously."""
    await asyncio.sleep(0.1)  # Simulate email sending
    print(f"Email sent to {to}: {subject}")
    return {"status": "sent", "to": to}

@executor.task(max_retries=5, retry_delay=2.0)
async def fetch_data(url: str):
    """Fetch data with automatic retries."""
    # Your HTTP request logic here
    return {"data": "..."}

# Execute tasks
async def main():
    async with executor:
        # Submit tasks
        task_id = await executor.submit(send_email, "user@example.com", "Hello", "World")

        # Wait for result
        result = await executor.wait_for_result(task_id, timeout=10.0)
        print(f"Result: {result.result}")

asyncio.run(main())
```

## Core Concepts

### Task Registration

Register async functions as tasks using the `@executor.task()` decorator:

```python
@executor.task(name="custom_name", max_retries=3, retry_delay=1.0)
async def my_task(arg1: str, arg2: int):
    # Task logic here
    return result
```

**Parameters:**
- `name` - Custom task name (defaults to function name)
- `max_retries` - Number of retry attempts on failure (default: 3)
- `retry_delay` - Seconds between retries (default: 1.0)
- `cpu_bound` - Use ProcessPoolExecutor for CPU-heavy tasks (default: False)

### Task Submission

Submit tasks for execution and get a unique task ID:

```python
# Submit with positional arguments
task_id = await executor.submit(my_task, "hello", 42)

# Submit with keyword arguments
task_id = await executor.submit(my_task, arg1="hello", arg2=42)

# Submit with priority (lower number = higher priority)
task_id = await executor.submit(my_task, "hello", 42, priority=1)
```

### Result Retrieval

Get task results using the task ID:

```python
# Wait for result with timeout
result = await executor.wait_for_result(task_id, timeout=30.0)

# Check result status
if result.status == TaskStatus.SUCCESS:
    print(f"Success: {result.result}")
elif result.status == TaskStatus.FAILED:
    print(f"Failed: {result.error}")

# Get result without waiting (returns None if not ready)
result = await executor.get_result(task_id)
```

### CPU-Bound Tasks

For CPU-intensive operations, use `cpu_bound=True` to run in a separate process:

```python
# Define at module level (required for pickling)
def compute_fibonacci(n: int) -> int:
    """Compute Fibonacci number."""
    if n <= 1:
        return n
    return compute_fibonacci(n-1) + compute_fibonacci(n-2)

# Register as CPU-bound task
executor = AsyncTaskExecutor(num_workers=4, cpu_workers=2)

@executor.task(cpu_bound=True)
def heavy_computation(data: list):
    # CPU-intensive work here
    return process_data(data)
```

**Important:** CPU-bound tasks must be regular functions (not async) and defined at module level for ProcessPoolExecutor pickling.

## Framework Integration

### FastAPI Integration

Perfect for background tasks in FastAPI applications:

```python
from fastapi import FastAPI, BackgroundTasks
from flowrra import AsyncTaskExecutor
from contextlib import asynccontextmanager

# Initialize executor
executor = AsyncTaskExecutor(num_workers=10)

@executor.task(max_retries=3)
async def send_welcome_email(email: str, username: str):
    """Send welcome email to new users."""
    # Your email logic here
    await asyncio.sleep(1)
    return {"email": email, "sent": True}

@executor.task()
async def process_upload(file_path: str, user_id: int):
    """Process uploaded file in background."""
    # Your processing logic
    return {"processed": True, "file": file_path}

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start executor
    await executor.start()
    yield
    # Shutdown: Stop executor
    await executor.stop()

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

@app.post("/register")
async def register_user(email: str, username: str):
    """Register user and send welcome email."""
    # Save user to database...

    # Submit background task
    task_id = await executor.submit(send_welcome_email, email, username)

    return {
        "user_id": 123,
        "email_task_id": task_id,
        "message": "Registration successful"
    }

@app.post("/upload")
async def upload_file(file_path: str, user_id: int):
    """Upload file and process in background."""
    # Save file...

    # Submit processing task
    task_id = await executor.submit(process_upload, file_path, user_id)

    return {
        "task_id": task_id,
        "status": "processing"
    }

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Check task status."""
    result = await executor.get_result(task_id)

    if result is None:
        return {"status": "not_found"}

    return {
        "task_id": task_id,
        "status": result.status.value,
        "result": result.result,
        "error": result.error
    }
```

### Django Integration

Use Flowrra in Django applications with async views:

```python
# tasks.py
import asyncio
from flowrra import AsyncTaskExecutor

# Initialize executor (consider using django.conf for settings)
executor = AsyncTaskExecutor(num_workers=10)

@executor.task(max_retries=3, retry_delay=2.0)
async def send_notification(user_id: int, message: str):
    """Send notification to user."""
    from myapp.models import User
    from asgiref.sync import sync_to_async

    # Use sync_to_async for Django ORM queries
    user = await sync_to_async(User.objects.get)(id=user_id)
    # Send notification logic...
    return {"user": user.email, "sent": True}

@executor.task()
async def generate_report(report_id: int):
    """Generate report asynchronously."""
    from myapp.models import Report
    from asgiref.sync import sync_to_async

    report = await sync_to_async(Report.objects.get)(id=report_id)
    # Generate report...
    report.status = "completed"
    await sync_to_async(report.save)()
    return {"report_id": report_id, "status": "completed"}
```

```python
# views.py
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from .tasks import executor, send_notification, generate_report

# Option 1: Async view (Django 4.1+)
async def create_notification(request):
    """Async view to create notification."""
    user_id = request.POST.get('user_id')
    message = request.POST.get('message')

    task_id = await executor.submit(send_notification, int(user_id), message)

    return JsonResponse({
        "task_id": task_id,
        "status": "submitted"
    })

# Option 2: Sync view with async_to_sync
def create_report(request):
    """Sync view using async task."""
    report_id = request.POST.get('report_id')

    # Wrap async call with async_to_sync
    task_id = async_to_sync(executor.submit)(generate_report, int(report_id))

    return JsonResponse({
        "task_id": task_id,
        "status": "processing"
    })

async def check_task(request, task_id):
    """Check task status."""
    result = await executor.get_result(task_id)

    if result is None:
        return JsonResponse({"error": "Task not found"}, status=404)

    return JsonResponse({
        "task_id": task_id,
        "status": result.status.value,
        "result": result.result
    })
```

```python
# asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# Start executor on application startup
from .tasks import executor
import asyncio

application = get_asgi_application()

# Start executor when Django starts
async def startup():
    await executor.start()

async def shutdown():
    await executor.stop()

# Run startup
asyncio.create_task(startup())
```

### Flask Integration

Use Flowrra with Flask and asyncio:

```python
from flask import Flask, jsonify, request
from flowrra import AsyncTaskExecutor
import asyncio
from functools import wraps

app = Flask(__name__)

# Initialize executor
executor = AsyncTaskExecutor(num_workers=8)

# Helper to run async functions in Flask
def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapped

# Register tasks
@executor.task(max_retries=3)
async def send_email_task(to: str, subject: str, body: str):
    """Send email asynchronously."""
    await asyncio.sleep(1)  # Simulate email sending
    return {"to": to, "subject": subject, "sent": True}

@executor.task()
async def process_data_task(data: dict):
    """Process data in background."""
    # Your processing logic
    await asyncio.sleep(2)
    return {"processed": True, "items": len(data)}

# Flask routes
@app.route('/send-email', methods=['POST'])
@async_route
async def send_email():
    """Submit email task."""
    data = request.get_json()

    task_id = await executor.submit(
        send_email_task,
        data['to'],
        data['subject'],
        data['body']
    )

    return jsonify({
        "task_id": task_id,
        "status": "submitted"
    })

@app.route('/process', methods=['POST'])
@async_route
async def process_data():
    """Submit processing task."""
    data = request.get_json()

    task_id = await executor.submit(process_data_task, data)

    return jsonify({
        "task_id": task_id,
        "status": "processing"
    })

@app.route('/task/<task_id>', methods=['GET'])
@async_route
async def get_task_status(task_id):
    """Get task status and result."""
    result = await executor.get_result(task_id)

    if result is None:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({
        "task_id": task_id,
        "status": result.status.value,
        "result": result.result,
        "error": result.error,
        "retries": result.retries
    })

# Application lifecycle
@app.before_serving
@async_route
async def before_serving():
    """Start executor before serving requests."""
    await executor.start()
    print("Executor started")

@app.after_serving
@async_route
async def after_serving():
    """Stop executor after serving."""
    await executor.stop()
    print("Executor stopped")

if __name__ == '__main__':
    # For development (use Gunicorn/Uvicorn for production)
    app.run(debug=True)
```

**Note:** For production Flask apps with Flowrra, consider using an ASGI server like Uvicorn or Hypercorn instead of the default WSGI server.

## Advanced Usage

### Priority Queues

Control task execution order with priorities:

```python
# Lower priority number = higher priority
await executor.submit(critical_task, priority=1)      # Executes first
await executor.submit(normal_task, priority=5)        # Executes second
await executor.submit(low_priority_task, priority=10) # Executes last
```

### Custom Retry Logic

Configure retry behavior per task:

```python
@executor.task(max_retries=5, retry_delay=2.0)
async def flaky_api_call(url: str):
    """API call with aggressive retries."""
    # Will retry up to 5 times with 2 second delay
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

### Error Handling

Handle task failures gracefully:

```python
@executor.task(max_retries=3)
async def risky_operation():
    """Operation that might fail."""
    if random.random() < 0.5:
        raise ValueError("Random failure")
    return "success"

# Check result
result = await executor.wait_for_result(task_id, timeout=10.0)

if result.status == TaskStatus.FAILED:
    print(f"Task failed after {result.retries} retries")
    print(f"Error: {result.error}")
elif result.status == TaskStatus.SUCCESS:
    print(f"Task succeeded: {result.result}")
```

### Custom Backends

Implement custom result storage backends:

```python
from flowrra.backends.base import BaseResultBackend
from flowrra.task import TaskResult

class RedisBackend(BaseResultBackend):
    """Redis-based result storage."""

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def store(self, task_id: str, result: TaskResult) -> None:
        """Store result in Redis."""
        await self.redis.set(f"task:{task_id}", result.to_dict())

    async def get(self, task_id: str) -> TaskResult | None:
        """Get result from Redis."""
        data = await self.redis.get(f"task:{task_id}")
        return TaskResult.from_dict(data) if data else None

    async def wait_for(self, task_id: str, timeout: float | None) -> TaskResult:
        """Wait for task completion."""
        # Implementation here
        pass

# Use custom backend
executor = AsyncTaskExecutor(
    num_workers=10,
    backend=RedisBackend("redis://localhost:6379")
)
```

## Configuration

### Executor Options

```python
executor = AsyncTaskExecutor(
    num_workers=10,        # Number of async I/O workers
    cpu_workers=4,         # Number of CPU-bound workers (ProcessPoolExecutor)
    backend=None,          # Custom result backend (defaults to InMemoryBackend)
)
```

### Task Options

```python
@executor.task(
    name="custom_name",    # Custom task name
    max_retries=3,         # Number of retry attempts
    retry_delay=1.0,       # Seconds between retries
    cpu_bound=False,       # Use ProcessPoolExecutor
)
async def my_task():
    pass
```

## Best Practices

1. **Use async for I/O-bound tasks** - Network requests, database queries, file I/O
2. **Use cpu_bound=True for CPU-heavy tasks** - Data processing, computations
3. **Set appropriate retry values** - Balance reliability with resource usage
4. **Use priority queues** - Critical tasks get priority=1, normal tasks priority=5
5. **Handle failures gracefully** - Check result status before using result
6. **Use context managers** - Ensures proper cleanup with `async with executor:`
7. **Module-level CPU tasks** - Define CPU-bound tasks at module level for pickling

## Performance Tips

- **Tune worker count** - Start with CPU core count for I/O workers
- **Batch similar tasks** - Group related operations for efficiency
- **Use timeouts** - Prevent tasks from hanging indefinitely
- **Monitor queue size** - Track pending tasks with `executor.pending_count()`
- **Profile bottlenecks** - Identify slow tasks and optimize

**Use Flowrra when:**
- Building async-first applications
- Want zero dependencies
- Don't need distributed workers
- Prefer simplicity over scalability

## API Reference

### AsyncTaskExecutor

```python
class AsyncTaskExecutor:
    def __init__(
        self,
        num_workers: int = 4,
        cpu_workers: int | None = None,
        backend: BaseResultBackend | None = None
    )

    def task(
        self,
        name: str | None = None,
        cpu_bound: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Callable

    async def submit(
        self,
        task_func: Callable,
        *args,
        priority: int = 0,
        **kwargs
    ) -> str

    async def wait_for_result(
        self,
        task_id: str,
        timeout: float | None = None
    ) -> TaskResult

    async def get_result(self, task_id: str) -> TaskResult | None

    async def start(self) -> None
    async def stop(self, wait: bool = True, timeout: float = 30.0) -> None

    def is_running(self) -> bool
    def pending_count(self) -> int
```

### TaskResult

```python
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
    def is_complete(self) -> bool
    @property
    def is_success(self) -> bool
```

### TaskStatus

```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=flowrra --cov-report=html

# Run specific test
pytest tests/test_executor.py::TestTaskExecution::test_simple_task_execution
```

### Code Quality

```bash
# Lint with ruff
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Type check with mypy
mypy src/flowrra/
```

## Requirements

- Python 3.11+
- Zero runtime dependencies

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Links

- **GitHub**: https://github.com/flowrra/flowrra
- **Documentation**: https://github.com/flowrra/flowrra#readme
- **Issues**: https://github.com/flowrra/flowrra/issues

## Acknowledgments

Inspired by Celery's elegant task queue design, built with modern Python async/await patterns.
