# Flowrra Management API

Pure Python API for querying and managing Flowrra applications. **No web framework dependencies** - can be used by CLI tools, web UI adapters, monitoring scripts, or any Python application.

## Overview

The Management API provides a clean interface to:
- Query system statistics (executor status, task counts)
- List and inspect registered tasks
- Check task results
- Perform health checks
- Query scheduler state (when scheduler is integrated)

## Installation

The Management API is included with Flowrra core - no additional dependencies required:

```bash
pip install flowrra
```

## Quick Start

```python
from flowrra import Flowrra
from flowrra.management import FlowrraManager

# Create your Flowrra app
app = Flowrra.from_urls()

# Create management interface
manager = FlowrraManager(app)

# Query system state
stats = await manager.get_stats()
tasks = await manager.list_registered_tasks()
health = await manager.health_check()
```

## API Reference

### FlowrraManager

Main management interface for Flowrra applications.

#### Constructor

```python
manager = FlowrraManager(app: Flowrra)
```

**Parameters:**
- `app`: Flowrra application instance

---

### System Statistics

#### `get_stats() -> Dict[str, Any]`

Get comprehensive system statistics.

```python
stats = await manager.get_stats()
```

**Returns:**

```python
{
    "app": {"running": bool},
    "executors": {
        "io": {"running": bool, "workers": int} | None,
        "cpu": {"running": bool, "workers": int} | None
    },
    "tasks": {
        "registered": int,
        "pending": int
    },
    "scheduler": {
        "enabled": bool,
        "schedules": int
    } | None
}
```

**Example:**

```python
stats = await manager.get_stats()
print(f"App running: {stats['app']['running']}")
print(f"Registered tasks: {stats['tasks']['registered']}")
if stats['executors']['io']:
    print(f"IO workers: {stats['executors']['io']['workers']}")
```

---

### Task Queries

#### `list_registered_tasks() -> List[Dict[str, Any]]`

List all registered tasks in the application.

```python
tasks = await manager.list_registered_tasks()
```

**Returns:**

```python
[
    {
        "name": str,
        "cpu_bound": bool,
        "max_retries": int,
        "retry_delay": float
    },
    ...
]
```

**Example:**

```python
tasks = await manager.list_registered_tasks()
for task in tasks:
    print(f"{task['name']}: retries={task['max_retries']}")
```

---

#### `get_task_info(task_name: str) -> Dict[str, Any] | None`

Get detailed information about a specific task.

```python
info = await manager.get_task_info("my_task")
```

**Parameters:**
- `task_name`: Name of the task to query

**Returns:**

```python
{
    "name": str,
    "cpu_bound": bool,
    "max_retries": int,
    "retry_delay": float,
    "module": str,
    "qualname": str
}
```

Or `None` if task not found.

**Example:**

```python
info = await manager.get_task_info("send_email")
if info:
    print(f"Task: {info['name']}")
    print(f"Module: {info['module']}")
    print(f"Max retries: {info['max_retries']}")
```

---

#### `get_task_result(task_id: str) -> Dict[str, Any] | None`

Get result of a completed task.

```python
result = await manager.get_task_result(task_id)
```

**Parameters:**
- `task_id`: Task identifier returned from `app.submit()`

**Returns:**

```python
{
    "task_id": str,
    "status": str,
    "result": Any,
    "error": str | None,
    "completed_at": datetime | None
}
```

Or `None` if task not found.

**Example:**

```python
task_id = await app.submit(my_task, arg1, arg2)
await asyncio.sleep(1)  # Wait for completion

result = await manager.get_task_result(task_id)
if result:
    print(f"Status: {result['status']}")
    print(f"Result: {result['result']}")
```

---

### Health Check

#### `health_check() -> Dict[str, Any]`

Perform comprehensive health check of the application.

```python
health = await manager.health_check()
```

**Returns:**

```python
{
    "healthy": bool,
    "timestamp": datetime,
    "components": {
        "app": {"healthy": bool, "message": str},
        "io_executor": {"healthy": bool, "message": str} | None,
        "cpu_executor": {"healthy": bool, "message": str} | None
    }
}
```

**Example:**

```python
health = await manager.health_check()
if health["healthy"]:
    print("System is healthy")
else:
    print("System has issues:")
    for component, status in health["components"].items():
        if status and not status["healthy"]:
            print(f"  - {component}: {status['message']}")
```

---

### Scheduler Queries

*Note: Scheduler integration methods are placeholders in Phase 1. They will be fully implemented when scheduler integration is added.*

#### `list_schedules(enabled_only: bool = False) -> List[Dict[str, Any]]`

List all scheduled tasks (placeholder).

#### `get_schedule(schedule_id: str) -> Dict[str, Any] | None`

Get details of a specific schedule (placeholder).

#### `get_scheduler_stats() -> Dict[str, Any] | None`

Get scheduler statistics (placeholder).

---

## Usage Examples

### Basic Monitoring Script

```python
import asyncio
from flowrra import Flowrra
from flowrra.management import FlowrraManager

async def monitor_app(app: Flowrra):
    """Simple monitoring script."""
    manager = FlowrraManager(app)

    while True:
        # Check health
        health = await manager.health_check()
        if not health["healthy"]:
            print("WARNING: System unhealthy!")

        # Get stats
        stats = await manager.get_stats()
        print(f"Pending tasks: {stats['tasks']['pending']}")

        # Wait 5 seconds
        await asyncio.sleep(5)

# Run monitoring
app = Flowrra.from_urls()
await app.start()
await monitor_app(app)
```

---

### Task Inspection Tool

```python
from flowrra.management import FlowrraManager

async def inspect_tasks(app: Flowrra):
    """List all tasks with their configuration."""
    manager = FlowrraManager(app)

    tasks = await manager.list_registered_tasks()

    print("Registered Tasks:")
    print("=" * 60)
    for task in tasks:
        info = await manager.get_task_info(task["name"])
        print(f"\nTask: {info['name']}")
        print(f"  Module: {info['module']}")
        print(f"  CPU Bound: {info['cpu_bound']}")
        print(f"  Max Retries: {info['max_retries']}")
        print(f"  Retry Delay: {info['retry_delay']}s")
```

---

### Health Check Endpoint

```python
from flowrra.management import FlowrraManager

async def health_endpoint(app: Flowrra) -> dict:
    """Simple health check for monitoring systems."""
    manager = FlowrraManager(app)
    health = await manager.health_check()

    # Return health status for monitoring
    return {
        "status": "healthy" if health["healthy"] else "unhealthy",
        "timestamp": health["timestamp"].isoformat(),
        "details": health["components"]
    }
```

---

## Integration with Web Frameworks

The Management API is designed to be framework-agnostic. It can be easily integrated into any web framework:

### FastAPI Example

```python
from fastapi import FastAPI
from flowrra import Flowrra
from flowrra.management import FlowrraManager

app = FastAPI()
flowrra = Flowrra.from_urls()
manager = FlowrraManager(flowrra)

@app.get("/api/stats")
async def get_stats():
    return await manager.get_stats()

@app.get("/api/health")
async def health():
    return await manager.health_check()

@app.get("/api/tasks")
async def list_tasks():
    return await manager.list_registered_tasks()
```

### Flask Example

```python
from flask import Flask, jsonify
import asyncio
from flowrra import Flowrra
from flowrra.management import FlowrraManager

app = Flask(__name__)
flowrra = Flowrra.from_urls()
manager = FlowrraManager(flowrra)

@app.route("/api/stats")
def get_stats():
    stats = asyncio.run(manager.get_stats())
    return jsonify(stats)

@app.route("/api/health")
def health():
    health = asyncio.run(manager.health_check())
    return jsonify(health)
```

---

## Design Principles

1. **Framework Agnostic**: No web framework dependencies in core API
2. **Pure Python**: All methods are async Python functions
3. **Simple Interface**: Easy to understand and use
4. **Composable**: Can be wrapped by web frameworks, CLI tools, or monitoring systems
5. **Extensible**: New query methods can be added without breaking existing code

---

## Roadmap

### Phase 1 (Current)
- ✅ System statistics
- ✅ Task queries
- ✅ Health checks
- ✅ Basic task result retrieval

### Phase 2 (Planned)
- Scheduler integration queries
- Real-time task execution tracking
- Execution history queries

### Phase 3 (Future)
- Task cancellation controls
- Worker pool management
- Advanced metrics and analytics

---

## See Also

- [SCHEDULER.md](SCHEDULER.md) - Scheduler documentation
- [README.md](README.md) - Main Flowrra documentation
- [examples/management_api_example.py](examples/management_api_example.py) - Full example
