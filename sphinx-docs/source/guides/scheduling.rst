Task Scheduling
===============

Flowrra includes a powerful task scheduling system similar to Celery Beat, allowing you to schedule tasks to run at specific times, intervals, or using cron expressions.

Features
--------

* **Cron-based scheduling**: Use standard cron syntax for flexible scheduling
* **Interval-based scheduling**: Run tasks at fixed intervals
* **One-time scheduling**: Schedule tasks to run once at a specific time
* **Persistent storage**: Schedules survive application restarts
* **Multiple database backends**: SQLite (default), PostgreSQL, or MySQL
* **Priority support**: High-priority tasks execute first
* **Enable/disable tasks**: Turn scheduled tasks on or off without deleting them

Quick Start
-----------

Basic Setup
~~~~~~~~~~~

The recommended way to use the scheduler is through the ``Flowrra`` app's ``create_scheduler()`` method:

.. code-block:: python

    from flowrra import Flowrra
    import asyncio

    # Create Flowrra app
    app = Flowrra.from_urls()

    # Define a task
    @app.task()
    async def send_daily_report():
        print("Generating daily report...")
        return "Report sent"

    # Create scheduler (automatically integrated with app's executors)
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

.. note::
   When you create a scheduler using ``app.create_scheduler()``, it automatically integrates with your app's executors and starts/stops with the app lifecycle.

Advanced Setup
~~~~~~~~~~~~~~

For more control over the scheduler backend:

.. code-block:: python

    from flowrra import Flowrra

    app = Flowrra.from_urls()

    # Create scheduler with custom backend
    scheduler = app.create_scheduler(
        backend="postgresql://localhost/flowrra"  # Use PostgreSQL
    )

Scheduling Methods
------------------

1. Cron-based Scheduling
~~~~~~~~~~~~~~~~~~~~~~~~

Schedule tasks using standard cron expressions:

.. code-block:: python

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

**Cron Format**: ``minute hour day month weekday``

* ``minute``: 0-59
* ``hour``: 0-23
* ``day``: 1-31
* ``month``: 1-12
* ``weekday``: 0-7 (0 and 7 are Sunday)

**Special characters**:

* ``*``: Any value
* ``,``: Value list separator (e.g., ``1,3,5``)
* ``-``: Range of values (e.g., ``1-5``)
* ``/``: Step values (e.g., ``*/15`` = every 15 minutes)

2. Interval-based Scheduling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run tasks at fixed intervals:

.. code-block:: python

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

3. One-time Scheduling
~~~~~~~~~~~~~~~~~~~~~~

Schedule a task to run once at a specific time:

.. code-block:: python

    from datetime import datetime, timedelta

    # Run in 1 hour
    run_time = datetime.now() + timedelta(hours=1)
    await scheduler.schedule_once(
        task_name="one_time_task",
        run_at=run_time,
        args=(data,),
        description="Runs once in 1 hour"
    )

Task Management
---------------

List Scheduled Tasks
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Get all scheduled tasks
    all_tasks = await scheduler.list_scheduled_tasks()

    for task in all_tasks:
        print(f"Task: {task.task_name}")
        print(f"Schedule: {task.schedule}")
        print(f"Next run: {task.next_run_at}")
        print(f"Enabled: {task.enabled}")

Enable/Disable Tasks
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Disable a task (keeps it in database but won't execute)
    await scheduler.disable_task(task_id)

    # Re-enable a task
    await scheduler.enable_task(task_id)

Delete Scheduled Tasks
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Remove a scheduled task permanently
    deleted = await scheduler.unschedule(task_id)
    if deleted:
        print("Task removed successfully")

Database Backends
-----------------

SQLite (Default)
~~~~~~~~~~~~~~~~

SQLite is the default backend, perfect for single-instance deployments:

.. code-block:: python

    # Default SQLite (creates .flowrra_schedule.db)
    scheduler = app.create_scheduler()

    # Custom SQLite path
    scheduler = app.create_scheduler(backend="sqlite:///path/to/schedule.db")

PostgreSQL
~~~~~~~~~~

For distributed deployments with multiple scheduler instances:

.. code-block:: python

    # Requires: pip install flowrra[postgresql]

    scheduler = app.create_scheduler(
        backend="postgresql://user:password@localhost:5432/flowrra"
    )

MySQL
~~~~~

.. code-block:: python

    # Requires: pip install flowrra[mysql]

    scheduler = app.create_scheduler(
        backend="mysql://user:password@localhost:3306/flowrra"
    )

Integration with Executors
---------------------------

Automatic Integration (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The scheduler automatically integrates with your app's executors when created via ``app.create_scheduler()``:

.. code-block:: python

    from flowrra import Flowrra

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

        await asyncio.Event().wait()

**How it works:**

* The scheduler checks each task's ``cpu_bound`` attribute
* IO-bound tasks (async) are automatically routed to IOExecutor
* CPU-bound tasks (sync) are automatically routed to CPUExecutor
* No manual callback or routing logic needed!

Manual Integration (Advanced)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For advanced use cases, you can create the scheduler manually:

.. code-block:: python

    from flowrra.scheduler import Scheduler
    from flowrra.scheduler.backends import get_scheduler_backend

    # Manual scheduler setup (not recommended for most cases)
    scheduler = Scheduler(
        backend=get_scheduler_backend(),
        registry=app.registry,
        io_executor=app._io_executor,
        cpu_executor=app._cpu_executor
    )

.. warning::
   Manual setup requires manual start/stop management. The recommended approach is to use ``app.create_scheduler()`` which automatically handles integration and lifecycle.

Common Patterns
---------------

Daily Reports
~~~~~~~~~~~~~

.. code-block:: python

    # Generate report every day at 9 AM
    await scheduler.schedule_cron(
        task_name="generate_daily_report",
        cron="0 9 * * *",
        description="Daily report generation"
    )

Hourly Cleanup
~~~~~~~~~~~~~~

.. code-block:: python

    # Clean up old data every hour
    await scheduler.schedule_cron(
        task_name="cleanup_old_data",
        cron="0 * * * *",
        description="Hourly cleanup"
    )

Weekday Business Hours
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Send reminders during business hours on weekdays
    await scheduler.schedule_cron(
        task_name="send_reminders",
        cron="0 9-17 * * 1-5",  # 9 AM - 5 PM, Mon-Fri
        description="Business hours reminders"
    )

Best Practices
--------------

1. **Use meaningful task names**: Make task names descriptive and unique
2. **Add descriptions**: Include descriptions for scheduled tasks to document their purpose
3. **Set appropriate priorities**: Reserve high priorities for critical tasks
4. **Monitor task execution**: Log task executions for debugging and monitoring
5. **Handle errors gracefully**: Implement proper error handling in scheduled tasks
6. **Use environment variables**: Store database URLs in environment variables for different environments
7. **Test schedules**: Verify cron expressions produce expected run times before deploying
8. **Use appropriate databases**: SQLite for single-instance, PostgreSQL/MySQL for distributed

See Also
--------

* :doc:`../api/flowrra.scheduler` - Complete API reference
* :doc:`tasks` - Task definition and execution
* :doc:`executors` - Executor configuration
