# Task Scheduling

Flowrra includes a powerful task scheduling system similar to Celery Beat, allowing you to schedule tasks to run at specific times, intervals, or using cron expressions.

## Features

- **Cron-based scheduling**: Use standard cron syntax for flexible scheduling
- **Interval-based scheduling**: Run tasks at fixed intervals
- **One-time scheduling**: Schedule tasks to run once at a specific time
- **Persistent storage**: Schedules survive application restarts
- **Multiple database backends**: SQLite (default), PostgreSQL, or MySQL
- **Priority support**: High-priority tasks execute first
- **Enable/disable tasks**: Turn scheduled tasks on or off without deleting them

## Execution Guarantees

Understanding the scheduler's behavior is critical for designing reliable systems. Here are the explicit guarantees and limitations:

### ✅ What Flowrra Guarantees

**1. At-Least-Once Execution**
- Tasks will execute **at least once** per schedule
- If a task fails, retries are attempted based on `max_retries` configuration
- **Implication**: Your tasks must be idempotent (safe to run multiple times)

**2. Persistent Schedules**
- Scheduled tasks survive application restarts
- Schedule definitions are stored in the database
- Tasks missed during downtime are **not** retroactively executed

**3. Priority Ordering**
- When multiple tasks are due simultaneously, higher priority tasks execute first
- Priority only affects ordering, not execution guarantees

**4. State Consistency**
- Task state is updated atomically in the database
- `next_run_at` is calculated and stored after submission to executor

### ⚠️ What Flowrra Does NOT Guarantee

**1. Exactly-Once Execution**
- The same task **can execute multiple times** for a single schedule
- **Why**: No distributed locking mechanism between scheduler instances
- **Scenario**: Two scheduler instances may both see a due task and submit it

**Example of duplicate execution:**
```
Scheduler Instance A: Checks DB at 09:00:00 → Sees task is due → Submits task
Scheduler Instance B: Checks DB at 09:00:01 → Sees task is due → Submits task
(Both submit before next_run_at is updated)
```

**2. No Distributed Coordination**
- Multiple scheduler instances do **not** coordinate with each other
- No leader election or distributed locks
- Each scheduler independently polls the database

**3. No Crash Recovery for In-Flight Tasks**
- If scheduler crashes after submitting a task but before updating `next_run_at`, the task may run again
- **Mitigation**: Tasks are submitted to executor before updating database (fail-safe toward re-execution)

**4. No Retroactive Execution**
- Tasks missed during downtime are skipped
- Next execution is calculated from current time, not missed time
- **Example**: Daily task at 9 AM, scheduler down from 8 AM to 11 AM → Task runs at 9 AM next day, not immediately at 11 AM

### 🏗️ Architecture Considerations

**Single Scheduler Instance (Recommended)**
```python
# Simple, reliable, no duplicate executions
app = Flowrra.from_urls()
scheduler = app.create_scheduler()
await app.start()  # Automatically starts scheduler
```
- ✅ No duplicate executions
- ✅ Simple to reason about
- ❌ Single point of failure
- ❌ Scheduler downtime means missed schedules

**Multiple Scheduler Instances (Advanced)**
```python
# High availability but duplicate executions possible
# Run this on multiple servers
app = Flowrra.from_urls()
scheduler = app.create_scheduler(backend="postgresql://shared-db/flowrra")
await app.start()  # Automatically starts scheduler
```
- ✅ High availability
- ✅ Automatic failover
- ⚠️ Duplicate task executions possible
- ⚠️ Requires idempotent tasks

### 💡 Designing Idempotent Tasks

Since at-least-once execution is guaranteed, design tasks to be idempotent:

**❌ Not Idempotent:**
```python
@app.task()
async def charge_customer():
    # Bad: Running twice charges customer twice!
    await payment_api.charge(customer_id, amount)
```

**✅ Idempotent:**
```python
@app.task()
async def charge_customer():
    # Good: Check if already charged before charging
    if not await payment_api.is_charged(customer_id, invoice_id):
        await payment_api.charge(customer_id, amount, idempotency_key=invoice_id)
```

**Idempotency Strategies:**
1. **Check-then-act**: Verify state before performing action
2. **Idempotency keys**: Use unique identifiers to prevent duplicate operations
3. **Database constraints**: Use UNIQUE constraints to prevent duplicate inserts
4. **Compare-and-swap**: Use optimistic locking for updates

### 🔍 Monitoring Duplicate Executions

Track duplicate executions in your tasks:

```python
import time

@app.task()
async def monitored_task():
    task_run_id = f"{datetime.now().isoformat()}-{os.getpid()}"

    # Check if this exact schedule already executed
    existing = await db.query("SELECT * FROM task_executions WHERE schedule_time = ?", schedule_time)
    if existing:
        print(f"Duplicate execution detected: {task_run_id}")
        return  # Skip duplicate

    # Record execution
    await db.execute("INSERT INTO task_executions (schedule_time, run_id) VALUES (?, ?)",
                     schedule_time, task_run_id)

    # Perform actual work
    await do_work()
```

### 📊 Execution Timing & Precision

**How the Scheduler Works:**

The scheduler uses **intelligent dynamic sleep** - it calculates when the next task is due and sleeps precisely until then, waking up only when needed.

```python
scheduler = app.create_scheduler()
```

**Smart Scheduling Loop:**
```
1. Check database for tasks with next_run_at <= now
2. Submit all due tasks to executor
3. Update next_run_at for each task
4. Calculate time until next task is due (max 1 hour)
5. Sleep until next task is due
6. Repeat
```

**Key Characteristics:**

- ✅ **Highly accurate**: Wakes up precisely when tasks are due (±1s)
- ✅ **Resource efficient**: few database queries
- ✅ **Event-driven**: Sleeps until next task
- ✅ **Intelligent**: Automatically adjusts sleep based on schedule

**Execution Precision:**

The scheduler's precision is highly accurate with dynamic sleep:

- **Best case drift**: 0 seconds (wakes exactly when task is due)
- **Worst case drift**: 1 second (minimum sleep bound)
- **Average drift**: < 1 second
- **Max sleep**: 1 hour (to periodically refresh schedules)

> **Note**: The scheduler automatically calculates optimal sleep duration based on when tasks are actually due, with a maximum sleep of 1 hour to periodically refresh the schedule list.

**Example with Dynamic Sleep:**
```
Cron: "0 9 * * *" (9:00 AM daily)
Current time: 8:30 AM

Dynamic calculation:
- Next task due: 9:00 AM (30 minutes away)
- Sleep duration: 1800 seconds
- Wake time: Exactly 9:00 AM
- Execution time: 9:00:00 AM (0-1s drift)
```

**Key Characteristics:**

1. **Precision**: Tasks execute within ±1s of scheduled time, regardless of frequency

2. **No Drift**: Execution time doesn't drift because `next_run_at` is always calculated from absolute time, not relative to last execution

3. **Resource Efficient**: Scheduler wakes only when tasks are due, plus once per hour to refresh schedule list

4. **Self-Optimizing**: No configuration needed - the scheduler automatically calculates optimal wake times

**Basic Usage:**

```python
# Dynamic sleep works automatically for all task types
scheduler = app.create_scheduler()

# CRON schedules: Precise to the second
# Interval schedules: No drift accumulation
# One-time schedules: Execute at exact time
```

### 🚨 Failure Scenarios

**Scenario 1: Scheduler Crashes After Task Submission**
```
1. Scheduler reads due task from DB
2. Scheduler submits task to executor ✓
3. Scheduler crashes before updating next_run_at ✗
Result: Task executes, but next_run_at not updated
Next check: Task seen as due again → Re-executed
```

**Scenario 2: Database Unavailable**
```
1. Scheduler cannot connect to database
2. Error logged: "Scheduler error: ..."
3. Scheduler sleeps and retries next check
Result: Schedules pause until database recovers
```

**Scenario 3: Executor Queue Full**
```
1. Scheduler submits task to executor
2. Executor queue is full → Task rejected or waits
3. Scheduler updates next_run_at regardless
Result: Task may be lost if executor rejects it
```

### 📝 Summary Table

| Guarantee | Single Instance | Multiple Instances |
|-----------|----------------|-------------------|
| At-least-once execution | ✅ Yes | ✅ Yes |
| Exactly-once execution | ✅ Yes | ❌ No |
| High availability | ❌ No | ✅ Yes |
| Duplicate executions | ❌ No | ⚠️ Possible |
| Task idempotency required | ⚠️ Recommended | ✅ Required |
| Retroactive execution after downtime | ❌ No | ❌ No |

## Quick Start

### Basic Setup

```python
from flowrra import Flowrra
import asyncio

# Create Flowrra app
app = Flowrra.from_urls()

# Define a task
@app.task()
async def send_daily_report():
    print("Generating daily report...")
    # Your task logic here
    return "Report sent"

# Create scheduler (automatically integrated with app's executors)
# The scheduler is automatically registered and will start/stop with the app
scheduler = app.create_scheduler()

# Schedule and start
async def main():
    # Schedule the task to run daily at 9 AM
    await scheduler.schedule_cron(
        task_name="send_daily_report",
        cron="0 9 * * *",
        description="Daily report at 9 AM"
    )

    # Start app (automatically starts scheduler too)
    await app.start()

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Setup

For more control over the scheduler backend:

```python
from flowrra import Flowrra

app = Flowrra.from_urls()

# Create scheduler with custom backend
scheduler = app.create_scheduler(
    backend="postgresql://localhost/flowrra"  # Use PostgreSQL
)
```

## Scheduling Methods

### 1. Cron-based Scheduling

Schedule tasks using standard cron expressions:

```python
# Every day at 9:00 AM
await scheduler.schedule_cron(
    task_name="daily_task",
    cron="0 9 * * *",
    args=(1, 2),
    kwargs={"key": "value"}
)

# Every 5 minutes
await scheduler.schedule_cron(
    task_name="frequent_task",
    cron="*/5 * * * *"
)

# Every Monday at 8:30 AM
await scheduler.schedule_cron(
    task_name="weekly_task",
    cron="30 8 * * 1"
)

# Business hours (9 AM - 5 PM) on weekdays
await scheduler.schedule_cron(
    task_name="business_hours_task",
    cron="0 9-17 * * 1-5"
)
```

**Cron Format**: `minute hour day month weekday`

- `minute`: 0-59
- `hour`: 0-23
- `day`: 1-31
- `month`: 1-12
- `weekday`: 0-7 (0 and 7 are Sunday)

**Special characters**:
- `*`: Any value
- `,`: Value list separator (e.g., `1,3,5`)
- `-`: Range of values (e.g., `1-5`)
- `/`: Step values (e.g., `*/15` = every 15 minutes)

**Timezone Behavior**:

⚠️ **Important**: Cron expressions are evaluated in the **server's local timezone**, not UTC.

- If your server runs in EST and you schedule `"0 9 * * *"`, it executes at 9 AM EST
- If your server runs in PST and you schedule `"0 9 * * *"`, it executes at 9 AM PST
- Times will shift with daylight saving time changes

**Recommendations**:
- For single-server deployments: Use local time as expected
- For multi-region deployments: Consider running all servers in UTC and schedule times in UTC
- For consistent behavior: Set your server's timezone explicitly (e.g., `TZ=UTC` environment variable)

**Example with explicit timezone awareness**:
```python
import os

# Set timezone for the entire application
os.environ['TZ'] = 'UTC'

# Now all cron schedules use UTC
await scheduler.schedule_cron(
    task_name="daily_report",
    cron="0 14 * * *",  # 2 PM UTC = 9 AM EST
    description="Daily report at 9 AM EST"
)
```

### 2. Interval-based Scheduling

Run tasks at fixed intervals:

```python
# Every 5 minutes (300 seconds)
await scheduler.schedule_interval(
    task_name="periodic_task",
    interval=300,
    args=(arg1, arg2),
    description="Runs every 5 minutes"
)

# Every hour
await scheduler.schedule_interval(
    task_name="hourly_task",
    interval=3600
)

# Every 30 seconds
await scheduler.schedule_interval(
    task_name="fast_task",
    interval=30
)
```

### 3. One-time Scheduling

Schedule a task to run once at a specific time:

```python
from datetime import datetime, timedelta

# Run in 1 hour
run_time = datetime.now() + timedelta(hours=1)
await scheduler.schedule_once(
    task_name="one_time_task",
    run_at=run_time,
    args=(data,),
    description="Runs once in 1 hour"
)

# Run at specific date and time (uses server's local timezone)
specific_time = datetime(2024, 12, 31, 23, 59, 0)
await scheduler.schedule_once(
    task_name="new_year_task",
    run_at=specific_time
)
```

**Note**: One-time scheduling also uses the server's local timezone. The `run_at` datetime should be in the same timezone as your server. For timezone-aware scheduling, ensure your datetime objects match your server's timezone or set the `TZ` environment variable.

## Task Management

### List Scheduled Tasks

```python
# Get all scheduled tasks
all_tasks = await scheduler.list_scheduled_tasks()

for task in all_tasks:
    print(f"Task: {task.task_name}")
    print(f"Schedule: {task.schedule}")
    print(f"Next run: {task.next_run_at}")
    print(f"Enabled: {task.enabled}")
```

### Get Specific Task

```python
task = await scheduler.get_scheduled_task(task_id)
if task:
    print(f"Task {task.task_name} runs: {task.schedule}")
```

### Enable/Disable Tasks

```python
# Disable a task (keeps it in database but won't execute)
await scheduler.disable_task(task_id)

# Re-enable a task
await scheduler.enable_task(task_id)
```

### Delete Scheduled Tasks

```python
# Remove a scheduled task permanently
deleted = await scheduler.unschedule(task_id)
if deleted:
    print("Task removed successfully")
```

## Database Backends

### SQLite (Default)

SQLite is the default backend, perfect for single-instance deployments:

```python
# Default SQLite (creates .flowrra_schedule.db)
scheduler = app.create_scheduler()

# Custom SQLite path
scheduler = app.create_scheduler(backend="sqlite:///path/to/schedule.db")
```

### PostgreSQL

For distributed deployments with multiple scheduler instances:

```python
# Requires: pip install flowrra[postgresql]

scheduler = app.create_scheduler(
    backend="postgresql://user:password@localhost:5432/flowrra"
)
```

### MySQL

```python
# Requires: pip install flowrra[mysql]

scheduler = app.create_scheduler(
    backend="mysql://user:password@localhost:3306/flowrra"
)
```

## Configuration

### Using Config Classes

```python
from flowrra import Config, SchedulerConfig

config = Config(
    scheduler=SchedulerConfig(
        database_url="sqlite:///schedules.db",
        enabled=True
    )
)

# Create backend from config
scheduler_backend = config.create_scheduler_backend()
```

### Environment Variables

```bash
export FLOWRRA_SCHEDULER_ENABLED=true
export FLOWRRA_SCHEDULER_DATABASE_URL=postgresql://localhost/flowrra
```

```python
from flowrra import Config

# Load from environment
config = Config.from_env()

if config.scheduler and config.scheduler.enabled:
    scheduler_backend = config.create_scheduler_backend()
    scheduler = app.create_scheduler(backend=scheduler_backend)
    # Scheduler automatically starts with app.start()
```

## Advanced Features

### Task Priority

Tasks with higher priority execute first when multiple tasks are due:

```python
# High priority task
await scheduler.schedule_cron(
    task_name="critical_task",
    cron="0 * * * *",
    priority=10  # Higher priority
)

# Normal priority task
await scheduler.schedule_cron(
    task_name="normal_task",
    cron="0 * * * *",
    priority=0  # Default priority
)
```

### Custom Task IDs

Provide custom IDs for easier task management:

```python
task_id = await scheduler.schedule_cron(
    task_name="daily_backup",
    cron="0 2 * * *",
    task_id="backup-daily"  # Custom ID
)

# Later, manage using custom ID
await scheduler.disable_task("backup-daily")
```

### Task Retry Configuration

Configure retries for scheduled tasks:

```python
await scheduler.schedule_cron(
    task_name="flaky_task",
    cron="0 * * * *",
    max_retries=5,       # Retry up to 5 times
    retry_delay=60.0     # Wait 60 seconds between retries
)
```

## Integration with Executors

### Automatic Integration (Recommended)

The scheduler automatically integrates with your app's executors when created via `app.create_scheduler()`:

```python
from flowrra import Flowrra
import asyncio

# Create Flowrra app
app = Flowrra.from_urls()

# Define tasks (async for IOExecutor, sync for CPUExecutor)
@app.task()
async def io_task(message: str):
    print(f"IO task executed: {message}")
    return "done"

@app.task(cpu_bound=True)
def cpu_task(n: int):
    return sum(i ** 2 for i in range(n))

# Create scheduler - automatically routes tasks to correct executor
scheduler = app.create_scheduler()

async def main():
    # Schedule IO-bound task
    await scheduler.schedule_cron(
        task_name="io_task",
        cron="*/5 * * * *",
        args=("Hello from scheduler!",)
    )

    # Schedule CPU-bound task
    await scheduler.schedule_interval(
        task_name="cpu_task",
        interval=300,
        args=(1000000,)
    )

    # Start everything (automatically starts scheduler)
    await app.start()

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

**How it works:**
- The scheduler checks each task's `cpu_bound` attribute
- IO-bound tasks (async) are automatically routed to IOExecutor
- CPU-bound tasks (sync) are automatically routed to CPUExecutor
- No manual callback or routing logic needed!

### Manual Integration (Advanced)

For advanced use cases where you need direct access to Scheduler internals, you can still create it manually. However, **the recommended approach is to use `app.create_scheduler()`** which automatically handles integration and lifecycle:

```python
from flowrra import Flowrra
from flowrra.scheduler import Scheduler
from flowrra.scheduler.backends import get_scheduler_backend

app = Flowrra.from_urls()

# Recommended: Use app.create_scheduler() for automatic integration
scheduler = app.create_scheduler()

# Advanced: Manual scheduler setup (not recommended)
# Only use this if you need custom scheduler behavior not provided by app.create_scheduler()
scheduler = Scheduler(
    backend=get_scheduler_backend(),
    registry=app.registry,
    io_executor=app._io_executor,
    cpu_executor=app._cpu_executor
)
# Note: Manual setup requires manual start/stop management
```

### Backward Compatibility (Legacy)

The old callback pattern is still supported:

```python
scheduler = Scheduler(
    backend=get_scheduler_backend(),
    registry=app.registry
)

# Manual callback
async def submit_task(task_func, *args, **kwargs):
    if task_func.cpu_bound:
        await app._cpu_executor.submit(task_func, *args, **kwargs)
    else:
        await app._io_executor.submit(task_func, *args, **kwargs)

scheduler.set_submit_callback(submit_task)
```

## Common Patterns

### Daily Reports

```python
# Generate report every day at 9 AM
await scheduler.schedule_cron(
    task_name="generate_daily_report",
    cron="0 9 * * *",
    description="Daily report generation"
)
```

### Hourly Cleanup

```python
# Clean up old data every hour
await scheduler.schedule_cron(
    task_name="cleanup_old_data",
    cron="0 * * * *",
    description="Hourly cleanup"
)
```

### Weekday Business Hours

```python
# Send reminders during business hours on weekdays
await scheduler.schedule_cron(
    task_name="send_reminders",
    cron="0 9-17 * * 1-5",  # 9 AM - 5 PM, Mon-Fri
    description="Business hours reminders"
)
```

### Monthly Reports

```python
# First day of every month at midnight
await scheduler.schedule_cron(
    task_name="monthly_report",
    cron="0 0 1 * *",
    description="Monthly report"
)
```

### Health Checks

```python
# Check system health every 5 minutes
await scheduler.schedule_interval(
    task_name="health_check",
    interval=300,
    description="System health check"
)
```

## Best Practices

1. **Use meaningful task names**: Make task names descriptive and unique
2. **Add descriptions**: Include descriptions for scheduled tasks to document their purpose
3. **Set appropriate check intervals**: Balance between responsiveness and system load
4. **Use priority wisely**: Reserve high priorities for critical tasks
5. **Monitor task execution**: Log task executions for debugging and monitoring
6. **Handle errors gracefully**: Implement proper error handling in scheduled tasks
7. **Use environment variables**: Store database URLs in environment variables for different environments
8. **Test schedules**: Verify cron expressions produce expected run times before deploying
9. **Clean up old schedules**: Remove one-time tasks after they execute to keep the database clean
10. **Use appropriate databases**: SQLite for single-instance, PostgreSQL/MySQL for distributed
11. **Be timezone-aware**: Set `TZ` environment variable explicitly for consistent behavior across environments

## Troubleshooting

### Task Not Executing

1. Check if task is enabled:
   ```python
   task = await scheduler.get_scheduled_task(task_id)
   print(f"Enabled: {task.enabled}")
   ```

2. Verify next run time:
   ```python
   print(f"Next run: {task.next_run_at}")
   ```

3. Ensure scheduler is running:
   ```python
   print(f"Scheduler running: {scheduler.is_running}")
   ```

### Invalid Cron Expression

Use a cron expression validator or test your expression:

```python
from flowrra.scheduler.cron import CronExpression
from datetime import datetime

try:
    cron = CronExpression("0 9 * * *")
    next_run = cron.next_run()
    print(f"Next run: {next_run}")
except ValueError as e:
    print(f"Invalid cron: {e}")
```

### Database Connection Issues

Check database connectivity:

```python
try:
    backend = get_scheduler_backend("postgresql://localhost/flowrra")
    tasks = await backend.list_all()
    print(f"Connected successfully, found {len(tasks)} tasks")
except Exception as e:
    print(f"Database error: {e}")
```

### Timezone-Related Issues

**Problem**: Task runs at unexpected time (e.g., scheduled for 9 AM but runs at 2 PM)

**Solution**: Check your server's timezone:

```python
import time
import os

# Check current timezone
print(f"System timezone: {time.tzname}")
print(f"TZ environment: {os.environ.get('TZ', 'Not set')}")

# Set timezone explicitly
os.environ['TZ'] = 'UTC'
time.tzset()  # Apply timezone change

# Verify
from datetime import datetime
print(f"Current time: {datetime.now()}")
```

**Problem**: Tasks run at different times across multiple servers

**Solution**: Ensure all servers use the same timezone:

```bash
# In your deployment configuration or Docker container
export TZ=UTC

# Or in systemd service file
Environment="TZ=UTC"
```

**Problem**: Task times shift after daylight saving time change

**Expected behavior**: Times shift with DST since scheduler uses local time. To avoid this, use UTC:

```bash
# Set all servers to UTC to avoid DST shifts
export TZ=UTC
```

## API Reference

### Scheduler Class

```python
class Scheduler:
    def __init__(
        self,
        backend: BaseSchedulerBackend,
        registry: TaskRegistry,
        io_executor: IOExecutor | None = None,
        cpu_executor: CPUExecutor | None = None
    )

    async def start() -> None
    async def stop() -> None

    async def schedule_cron(
        task_name: str,
        cron: str,
        args: tuple = (),
        kwargs: dict | None = None,
        enabled: bool = True,
        description: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        priority: int = 0,
        task_id: str | None = None
    ) -> str

    async def schedule_interval(
        task_name: str,
        interval: float,
        args: tuple = (),
        kwargs: dict | None = None,
        enabled: bool = True,
        description: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        priority: int = 0,
        task_id: str | None = None
    ) -> str

    async def schedule_once(
        task_name: str,
        run_at: datetime,
        args: tuple = (),
        kwargs: dict | None = None,
        description: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        priority: int = 0,
        task_id: str | None = None
    ) -> str

    async def unschedule(task_id: str) -> bool
    async def enable_task(task_id: str) -> None
    async def disable_task(task_id: str) -> None
    async def get_scheduled_task(task_id: str) -> ScheduledTask | None
    async def list_scheduled_tasks() -> list[ScheduledTask]

    def set_submit_callback(callback: Callable) -> None

    @property
    def is_running() -> bool
```

### ScheduledTask Model

```python
@dataclass
class ScheduledTask:
    id: str
    task_name: str
    schedule_type: ScheduleType
    schedule: str
    args: tuple
    kwargs: dict
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime
    description: str | None
    max_retries: int
    retry_delay: float
    priority: int
```

### ScheduleType Enum

```python
class ScheduleType(Enum):
    CRON = "cron"
    INTERVAL = "interval"
    ONE_TIME = "one_time"
```
