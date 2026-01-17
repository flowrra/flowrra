# Flowrra

Lightweight async task queue built on pure Python asyncio. A Celery-inspired background job executor with zero dependencies, featuring retries, priority queues, and pluggable backends.

[![Documentation](https://readthedocs.org/projects/flowrra/badge/?version=latest)](https://flowrra.readthedocs.io/en/latest/)

📚 **[Read the Documentation](https://flowrra.readthedocs.io/en/latest/)** - Complete guides, API reference, and tutorials

## Features

- **Zero Dependencies** - Built on pure Python 3.11+ asyncio (only aiosqlite required for scheduler)
- **Simple API** - Decorator-based task registration, just like Celery
- **Async First** - Native async/await support for I/O-bound tasks
- **CPU-Bound Support** - ProcessPoolExecutor integration for compute-heavy tasks
- **Task Scheduling** - Celery Beat-like persistent scheduling with cron, intervals, and one-time tasks
- **Web UI** - Built-in monitoring dashboard for FastAPI, Flask/Quart, and Django
- **Automatic Retries** - Configurable retry logic with exponential backoff
- **Priority Queues** - Control task execution order
- **Pluggable Backends** - Extensible result storage (in-memory included)
- **Multiple Databases** - SQLite, PostgreSQL, and MySQL support for scheduler
- **Type Safe** - Full type hints for better IDE support

## Installation

```bash
pip install flowrra
```

With Redis backend support (for distributed execution):
```bash
pip install flowrra[redis]
```

With PostgreSQL scheduler support:
```bash
pip install flowrra[postgresql]
```

With MySQL scheduler support:
```bash
pip install flowrra[mysql]
```

With Web UI support:
```bash
# FastAPI
pip install flowrra[ui-fastapi]

# Flask/Quart
pip install flowrra[ui-flask]

# Django
pip install flowrra[ui-django]

# All UI adapters
pip install flowrra[ui]
```

With all optional dependencies:
```bash
pip install flowrra[all]
```

For development:
```bash
pip install flowrra[dev]
```

## Quick Start

### Basic Usage

```python
import asyncio
from flowrra import Flowrra

# Create Flowrra application
app = Flowrra.from_urls()

# Register I/O-bound tasks (async functions)
@app.task()
async def send_email(to: str, subject: str):
    """Send an email asynchronously."""
    await asyncio.sleep(0.1)  # Simulate email sending
    print(f"Email sent to {to}: {subject}")
    return {"status": "sent", "to": to}

@app.task(max_retries=5, retry_delay=2.0)
async def fetch_data(url: str):
    """Fetch data with automatic retries."""
    # Your HTTP request logic here
    return {"data": "..."}

# Execute tasks
async def main():
    async with app:
        # Submit tasks
        task_id = await app.submit(send_email, "user@example.com", "Hello")

        # Wait for result
        result = await app.wait_for_result(task_id, timeout=10.0)
        print(f"Result: {result.result}")

asyncio.run(main())
```

### CPU-Bound Tasks

For CPU-intensive computations, use `cpu_bound=True` with sync functions:

```python
import asyncio
from flowrra import Flowrra

# CPU tasks require Redis backend for cross-process result sharing
app = Flowrra.from_urls(backend="redis://localhost:6379/0")

# Register CPU-bound task (sync function, not async!)
@app.task(cpu_bound=True)
def compute_heavy(n: int):
    """CPU-intensive computation runs in separate process."""
    return sum(i ** 2 for i in range(n))

async def main():
    async with app:
        task_id = await app.submit(compute_heavy, 1000000)
        result = await app.wait_for_result(task_id, timeout=10.0)
        print(f"Result: {result.result}")

asyncio.run(main())
```

**Note**: CPU-bound tasks require a Redis backend. Install with `pip install flowrra[redis]` and ensure Redis is running.

### Distributed Task Queue

Use Redis broker for distributed task queueing across multiple workers:

```python
from flowrra import Flowrra

# Redis broker queues tasks, Redis backend stores results
app = Flowrra.from_urls(
    broker="redis://localhost:6379/0",   # Task queue
    backend="redis://localhost:6379/1"   # Result storage
)

@app.task()
async def process_job(job_id: int):
    # Workers pull tasks from Redis queue
    return f"Processed job {job_id}"
```

### Task Scheduling

Schedule tasks to run periodically using cron expressions, intervals, or one-time execution:

```python
from flowrra import Flowrra
import asyncio

# Create app and define tasks
app = Flowrra.from_urls()

@app.task()
async def send_daily_report():
    print("Generating daily report...")
    return "Report sent"

@app.task()
async def cleanup_old_data():
    print("Cleaning up old data...")
    return "Cleanup complete"

# Create integrated scheduler (automatically connected to app's executors)
scheduler = app.create_scheduler()

async def main():
    # Schedule tasks
    await scheduler.schedule_cron(
        task_name="send_daily_report",
        cron="0 9 * * *",  # Every day at 9 AM
        description="Daily report generation"
    )

    await scheduler.schedule_interval(
        task_name="cleanup_old_data",
        interval=3600,  # Every hour
        description="Hourly cleanup"
    )

    # Start app and scheduler
    await app.start()
    await scheduler.start()

    # Keep running
    await asyncio.Event().wait()

asyncio.run(main())
```

**Scheduling options**:
- **Cron**: `schedule_cron(task_name, cron="0 9 * * *")` - Standard cron syntax
- **Interval**: `schedule_interval(task_name, interval=300)` - Every N seconds
- **One-time**: `schedule_once(task_name, run_at=datetime)` - Run once at specific time

**Database backends**:
- SQLite (default): `get_scheduler_backend()`
- PostgreSQL: `get_scheduler_backend("postgresql://user:pass@host/db")`
- MySQL: `get_scheduler_backend("mysql://user:pass@host/db")`

See [SCHEDULER.md](SCHEDULER.md) for complete documentation.

## Core Concepts

### Task Registration

Register tasks using the `@app.task()` decorator:

**I/O-Bound Tasks** - Async functions for network, file I/O, API calls:

```python
from flowrra import Flowrra

app = Flowrra.from_urls()

@app.task(name="custom_name", max_retries=3, retry_delay=1.0)
async def my_io_task(arg1: str, arg2: int):
    # Must be async for I/O-bound tasks
    await asyncio.sleep(1)
    return result
```

**CPU-Bound Tasks** - Sync functions for heavy computations:

```python
from flowrra import Flowrra

# Requires Redis backend for cross-process result sharing
app = Flowrra.from_urls(backend="redis://localhost:6379/0")

@app.task(cpu_bound=True, max_retries=3, retry_delay=1.0)
def my_cpu_task(arg1: str, arg2: int):
    # Must be sync (not async) for CPU-bound tasks
    return compute_result(arg1, arg2)
```

**Parameters:**
- `name` - Custom task name (defaults to function name)
- `max_retries` - Number of retry attempts on failure (default: 3)
- `retry_delay` - Seconds between retries (default: 1.0)

### Task Submission

Submit tasks for execution and get a unique task ID:

```python
# Submit with positional arguments
task_id = await app.submit(my_task, "hello", 42)

# Submit with keyword arguments
task_id = await app.submit(my_task, arg1="hello", arg2=42)

# Submit with priority (lower number = higher priority)
task_id = await app.submit(my_task, "hello", 42, priority=1)
```

### Result Retrieval

Get task results using the task ID:

```python
# Wait for result with timeout
result = await app.wait_for_result(task_id, timeout=30.0)

# Check result status
if result.status == TaskStatus.SUCCESS:
    print(f"Success: {result.result}")
elif result.status == TaskStatus.FAILED:
    print(f"Failed: {result.error}")

# Get result without waiting (returns None if not ready)
result = await app.get_result(task_id)
```

### Redis Backend for Distributed Execution

For production deployments and distributed task execution, configure Redis when creating your Flowrra app:

```python
from flowrra import Flowrra

# Flowrra with Redis backend and broker
app = Flowrra.from_urls(
    broker="redis://localhost:6379/0",   # Task queue
    backend="redis://localhost:6379/1"   # Result storage
)

# Task registration works the same
@app.task()
async def my_io_task(data: str):
    return await process(data)

@app.task(cpu_bound=True)
def my_cpu_task(n: int):
    return compute(n)
```

**Supported Redis connection strings:**
- Basic: `redis://localhost:6379/0`
- With password: `redis://:password@localhost:6379/0`
- With username: `redis://username:password@localhost:6379/0`
- SSL/TLS: `rediss://localhost:6379/0`
- Unix socket: `unix:///tmp/redis.sock`

**Important:**
- CPU-bound tasks must be regular functions (not async)
- Tasks must be defined at module level for ProcessPoolExecutor pickling
- CPU-bound tasks require Redis backend for cross-process result sharing
- Install Redis support: `pip install flowrra[redis]`

## Framework Integration

### FastAPI Integration

Perfect for background tasks in FastAPI applications:

```python
from fastapi import FastAPI
from flowrra import Flowrra
from contextlib import asynccontextmanager

# Initialize Flowrra app
flowrra_app = Flowrra.from_urls()

@flowrra_app.task(max_retries=3)
async def send_welcome_email(email: str, username: str):
    """Send welcome email to new users."""
    # Your email logic here
    await asyncio.sleep(1)
    return {"email": email, "sent": True}

@flowrra_app.task()
async def process_upload(file_path: str, user_id: int):
    """Process uploaded file in background."""
    # Your processing logic
    return {"processed": True, "file": file_path}

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Flowrra
    await flowrra_app.start()
    yield
    # Shutdown: Stop Flowrra
    await flowrra_app.stop()

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

@app.post("/register")
async def register_user(email: str, username: str):
    """Register user and send welcome email."""
    # Save user to database...

    # Submit background task
    task_id = await flowrra_app.submit(send_welcome_email, email, username)

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
    task_id = await flowrra_app.submit(process_upload, file_path, user_id)

    return {
        "task_id": task_id,
        "status": "processing"
    }

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Check task status."""
    result = await flowrra_app.get_result(task_id)

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
from flowrra import Flowrra

# Initialize Flowrra app (consider using django.conf for settings)
app = Flowrra.from_urls()

@app.task(max_retries=3, retry_delay=2.0)
async def send_notification(user_id: int, message: str):
    """Send notification to user."""
    from myapp.models import User
    from asgiref.sync import sync_to_async

    # Use sync_to_async for Django ORM queries
    user = await sync_to_async(User.objects.get)(id=user_id)
    # Send notification logic...
    return {"user": user.email, "sent": True}

@app.task()
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
from .tasks import app, send_notification, generate_report

# Option 1: Async view (Django 4.1+)
async def create_notification(request):
    """Async view to create notification."""
    user_id = request.POST.get('user_id')
    message = request.POST.get('message')

    task_id = await app.submit(send_notification, int(user_id), message)

    return JsonResponse({
        "task_id": task_id,
        "status": "submitted"
    })

# Option 2: Sync view with async_to_sync
def create_report(request):
    """Sync view using async task."""
    report_id = request.POST.get('report_id')

    # Wrap async call with async_to_sync
    task_id = async_to_sync(app.submit)(generate_report, int(report_id))

    return JsonResponse({
        "task_id": task_id,
        "status": "processing"
    })

async def check_task(request, task_id):
    """Check task status."""
    result = await app.get_result(task_id)

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

# Start Flowrra on application startup
from .tasks import app
import asyncio

application = get_asgi_application()

# Start Flowrra when Django starts
async def startup():
    await app.start()

async def shutdown():
    await app.stop()

# Run startup
asyncio.create_task(startup())
```

### Flask Integration

Use Flowrra with Flask and asyncio:

```python
from flask import Flask, jsonify, request
from flowrra import Flowrra
import asyncio
from functools import wraps

flask_app = Flask(__name__)

# Initialize Flowrra app
flowrra_app = Flowrra.from_urls()

# Helper to run async functions in Flask
def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapped

# Register tasks
@flowrra_app.task(max_retries=3)
async def send_email_task(to: str, subject: str, body: str):
    """Send email asynchronously."""
    await asyncio.sleep(1)  # Simulate email sending
    return {"to": to, "subject": subject, "sent": True}

@flowrra_app.task()
async def process_data_task(data: dict):
    """Process data in background."""
    # Your processing logic
    await asyncio.sleep(2)
    return {"processed": True, "items": len(data)}

# Flask routes
@flask_app.route('/send-email', methods=['POST'])
@async_route
async def send_email():
    """Submit email task."""
    data = request.get_json()

    task_id = await flowrra_app.submit(
        send_email_task,
        data['to'],
        data['subject'],
        data['body']
    )

    return jsonify({
        "task_id": task_id,
        "status": "submitted"
    })

@flask_app.route('/process', methods=['POST'])
@async_route
async def process_data():
    """Submit processing task."""
    data = request.get_json()

    task_id = await flowrra_app.submit(process_data_task, data)

    return jsonify({
        "task_id": task_id,
        "status": "processing"
    })

@flask_app.route('/task/<task_id>', methods=['GET'])
@async_route
async def get_task_status(task_id):
    """Get task status and result."""
    result = await flowrra_app.get_result(task_id)

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
@flask_app.before_serving
@async_route
async def before_serving():
    """Start Flowrra before serving requests."""
    await flowrra_app.start()
    print("Flowrra started")

@flask_app.after_serving
@async_route
async def after_serving():
    """Stop Flowrra after serving."""
    await flowrra_app.stop()
    print("Flowrra stopped")

if __name__ == '__main__':
    # For development (use Gunicorn/Uvicorn for production)
    flask_app.run(debug=True)
```

**Note:** For production Flask apps with Flowrra, consider using an ASGI server like Uvicorn or Hypercorn instead of the default WSGI server.

## Web UI

Flowrra includes built-in web interfaces for monitoring and managing your tasks. Mount the UI into your existing web application to get instant visibility into task execution, schedules, and system health.

### Features

- 📊 **Dashboard** - System overview with real-time statistics
- 📋 **Task Management** - View registered tasks and execution history
- 📅 **Schedule Management** - Create and manage cron schedules
- 🔧 **JSON API** - RESTful endpoints for programmatic access
- ⚡ **Multiple Frameworks** - FastAPI, Flask/Quart, and Django support
- 🔌 **WebSocket Support** - Optional real-time task updates (no page refresh needed)

### Quick Start

**FastAPI:**
```python
from fastapi import FastAPI
from flowrra import Flowrra
from flowrra.ui.fastapi import create_router

app = FastAPI()
flowrra = Flowrra.from_urls()

# Mount Flowrra UI
app.include_router(create_router(flowrra), prefix="/flowrra")

# Visit: http://localhost:8000/flowrra/
```

**Flask/Quart:**
```python
from quart import Quart
from flowrra import Flowrra
from flowrra.ui.flask import create_blueprint

app = Quart(__name__)
flowrra = Flowrra.from_urls()

# Mount Flowrra UI
app.register_blueprint(create_blueprint(flowrra), url_prefix="/flowrra")

# Visit: http://localhost:8000/flowrra/
```

**Django:**
```python
# urls.py
from django.urls import path, include
from flowrra.ui.django import get_urls

urlpatterns = [
    path('flowrra/', include(get_urls(flowrra))),
]

# Visit: http://localhost:8000/flowrra/
```

### Installation

```bash
# FastAPI
pip install flowrra[ui-fastapi]

# Flask/Quart
pip install flowrra[ui-flask]

# Django
pip install flowrra[ui-django]

# All UI adapters
pip install flowrra[ui]
```

### API Endpoints

All UI adapters provide these JSON API endpoints:

- `GET /api/stats` - System statistics
- `GET /api/health` - Health check
- `GET /api/tasks` - List registered tasks
- `GET /api/tasks/{name}` - Task details
- `GET /api/schedules` - List schedules
- `POST /api/schedules/cron` - Create schedule
- `PUT /api/schedules/{id}/enable` - Enable schedule
- `PUT /api/schedules/{id}/disable` - Disable schedule
- `DELETE /api/schedules/{id}` - Delete schedule

### Real-Time Updates (WebSocket)

The UI supports optional WebSocket connections for real-time task updates without page refreshes:

- **FastAPI**: WebSocket support is built-in and enabled automatically
- **Django**: Requires Django-Channels setup (see [WEBSOCKET_SETUP.md](docs/WEBSOCKET_SETUP.md))
- **Flask/Quart**: Requires migration to Quart (see [WEBSOCKET_SETUP.md](docs/WEBSOCKET_SETUP.md))

**Without WebSocket**, the frontend automatically falls back to polling every 15 seconds. Both modes work seamlessly!

### Full Documentation

See [UI.md](UI.md) for complete documentation including:
- Detailed integration guides for each framework
- API endpoint reference
- Customization and styling
- Authentication setup
- Production deployment
- Troubleshooting

See [docs/WEBSOCKET_SETUP.md](docs/WEBSOCKET_SETUP.md) for WebSocket configuration:
- Django-Channels setup guide
- Flask to Quart migration
- Testing WebSocket connections
- Production deployment considerations

## Advanced Usage

### Priority Queues

Control task execution order with priorities:

```python
# Lower priority number = higher priority
await app.submit(critical_task, priority=1)      # Executes first
await app.submit(normal_task, priority=5)        # Executes second
await app.submit(low_priority_task, priority=10) # Executes last
```

### Custom Retry Logic

Configure retry behavior per task:

```python
@app.task(max_retries=5, retry_delay=2.0)
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
@app.task(max_retries=3)
async def risky_operation():
    """Operation that might fail."""
    if random.random() < 0.5:
        raise ValueError("Random failure")
    return "success"

# Check result
result = await app.wait_for_result(task_id, timeout=10.0)

if result.status == TaskStatus.FAILED:
    print(f"Task failed after {result.retries} retries")
    print(f"Error: {result.error}")
elif result.status == TaskStatus.SUCCESS:
    print(f"Task succeeded: {result.result}")
```

### Custom Backends

Flowrra includes a Redis backend, or you can implement your own. For most use cases, we recommend using Redis:

```python
from flowrra import Flowrra

# Recommended: Use Redis backend with connection string
app = Flowrra.from_urls(
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

# Or with Config
from flowrra import Config, BrokerConfig, BackendConfig

config = Config(
    broker=BrokerConfig(url="redis://localhost:6379/0"),
    backend=BackendConfig(url="redis://localhost:6379/1", ttl=3600)
)
app = Flowrra(config=config)
```

**Built-in backends:**
- `InMemoryBackend` - Default, single-process (automatically used when no backend specified)
- `RedisBackend` - Production-ready, distributed (via connection string)

## Configuration

### Flowrra Configuration

**Using URLs** (recommended):
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

**Using Config objects** (advanced):
```python
from flowrra import Flowrra, Config, BrokerConfig, BackendConfig, ExecutorConfig

config = Config(
    broker=BrokerConfig(
        url="redis://localhost:6379/0",
        max_connections=50,
        socket_timeout=5.0
    ),
    backend=BackendConfig(
        url="redis://localhost:6379/1",
        ttl=3600,  # Result expiration in seconds
        max_connections=50
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

### Task Options

```python
@app.task(
    name="custom_name",    # Custom task name (defaults to function name)
    max_retries=3,         # Number of retry attempts (default: 3)
    retry_delay=1.0,       # Seconds between retries (default: 1.0)
    cpu_bound=False,       # True for CPU-bound, False for I/O-bound (default)
)
async def my_task():     # async for I/O-bound, sync for cpu_bound=True
    pass
```

## Best Practices

1. **Use async for I/O-bound tasks** - Network requests, database queries, file I/O (default)
2. **Use cpu_bound=True for CPU-heavy tasks** - Data processing, computations, image processing
3. **Use Redis for production** - Install `flowrra[redis]` and configure broker/backend URLs
4. **Set appropriate retry values** - Balance reliability with resource usage
5. **Use priority queues** - Critical tasks get priority=1, normal tasks priority=5
6. **Handle failures gracefully** - Check result status before using result
7. **Use context managers** - Ensures proper cleanup with `async with app:`
8. **Module-level CPU tasks** - Define CPU-bound tasks at module level for pickling

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

### Flowrra

Unified application for I/O-bound and CPU-bound task execution:

```python
class Flowrra:
    def __init__(self, config: Config | None = None)

    @classmethod
    def from_urls(
        cls,
        broker: str | None = None,
        backend: str | None = None,
    ) -> "Flowrra"

    def task(
        self,
        name: str | None = None,
        cpu_bound: bool = False,  # False = I/O-bound (async), True = CPU-bound (sync)
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
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

    @property
    def is_running(self) -> bool
```

### Config

Configuration for Flowrra application:

```python
@dataclass
class Config:
    broker: BrokerConfig | None = None
    backend: BackendConfig | None = None
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)

    @classmethod
    def from_env(cls, prefix: str = "FLOWRRA_") -> "Config"

@dataclass
class BrokerConfig:
    url: str
    max_connections: int = 50
    socket_timeout: float = 5.0
    retry_on_timeout: bool = True

@dataclass
class BackendConfig:
    url: str
    ttl: int | None = None
    max_connections: int = 50
    socket_timeout: float = 5.0
    retry_on_timeout: bool = True

@dataclass
class ExecutorConfig:
    num_workers: int = 4          # Async workers for I/O tasks
    cpu_workers: int | None = None # Process workers for CPU tasks
    max_queue_size: int = 1000
    max_retries: int = 3
    retry_delay: float = 1.0
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
- Zero runtime dependencies (core functionality)
- Optional: `redis[hiredis]>=5.0.0` for Redis backend support

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

- **Documentation**: https://flowrra.readthedocs.io/en/latest/
- **GitHub**: https://github.com/flowrra/flowrra
- **Issues**: https://github.com/flowrra/flowrra/issues
- **PyPI**: https://pypi.org/project/flowrra/ (when published)

## Acknowledgments

Inspired by Celery's elegant task queue design, built with modern Python async/await patterns.
