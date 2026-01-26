Quick Start
===========

This guide will help you get started with Flowrra in minutes.


Basic Usage
-----------

Here's a simple example of creating and running tasks:

.. code-block:: python

   import asyncio
   from flowrra import Flowrra

   # Create Flowrra application
   app = Flowrra.from_urls()

   # Register tasks
   @app.task()
   async def send_email(to: str, subject: str):
       """Send an email asynchronously."""
       await asyncio.sleep(0.1)  # Simulate email sending
       print(f"Email sent to {to}: {subject}")
       return {"status": "sent", "to": to}

   # Execute tasks
   async def main():
       async with app:
           # Submit a task
           task_id = await app.submit(send_email, "user@example.com", "Hello")
           
           # Wait for result
           result = await app.wait_for_result(task_id, timeout=10.0)
           print(f"Result: {result.result}")

   asyncio.run(main())


Default Configuration
----------------------

When you create a Flowrra application using ``Flowrra.from_urls()`` without any parameters,
it uses the following defaults:

**Task Queue (Broker)**

* **In-memory queue** (``asyncio.PriorityQueue``) by default
* Tasks are stored in memory and will be lost if the application restarts
* Best for development, testing, and single-process applications
* **For production**, Redis broker is strongly recommended for persistence and distributed workers

**Result Storage (Backend)**

* **InMemoryBackend** for I/O-bound tasks
* Results are stored in memory
* For CPU-bound tasks, a persistent backend (Redis, PostgreSQL, or MySQL) is **required** for cross-process result storage
* Note: CPU tasks can still use the in-memory broker/queue

**Executor Configuration**

* **I/O Workers**: 4 concurrent workers
* **CPU Workers**: Defaults to the number of CPU cores (e.g., 8 on an 8-core system)
* **Max Queue Size**: 1000 tasks
* **Max Retries**: 3 attempts per task
* **Retry Delay**: 1.0 second between retries

Example with explicit configuration:

.. code-block:: python

   from flowrra import Flowrra, Config, ExecutorConfig

   import os

   # Explicitly specify the same defaults
   config = Config(
       executor=ExecutorConfig(
           io_workers=4,                      # 4 concurrent I/O tasks
           cpu_workers=os.cpu_count(),        # Number of CPU cores
           max_queue_size=1000,               # Queue up to 1000 tasks
           max_retries=3,                     # Retry failed tasks 3 times
           retry_delay=1.0                    # Wait 1 second between retries
       )
   )
   app = Flowrra(config=config)

For **production deployments** or **distributed workers**, use Redis for both broker and backend:

.. code-block:: python

   # Both broker and backend using Redis (recommended for production)
   app = Flowrra.from_urls(
       broker='redis://localhost:6379/0',   # Persistent queue, supports distributed workers
       backend='redis://localhost:6379/1'   # Result storage
   )

   # Or just backend for CPU tasks in single-instance deployment
   app = Flowrra.from_urls(
       backend='redis://localhost:6379/1'   # Backend only (broker defaults to in-memory)
   )


Task Configuration
------------------

Configure retry behavior and other options:

.. code-block:: python

   @app.task(max_retries=5, retry_delay=2.0, priority=10)
   async def fetch_data(url: str):
       """Fetch data with retries and custom priority."""
       # Your HTTP request logic here
       return {"data": "..."}


CPU-Bound Tasks
---------------

For CPU-intensive operations, use the ``cpu_bound`` parameter.

.. important::
   CPU-bound tasks **must be synchronous functions** (not async). They run in separate processes
   using ``ProcessPoolExecutor`` and require a persistent **backend** (Redis, PostgreSQL, or MySQL)
   for cross-process result storage. The broker/queue can remain in-memory.

.. code-block:: python

   @app.task(cpu_bound=True)
   def compute_heavy_operation(n: int):  # Note: NOT async
       """CPU-intensive task using ProcessPoolExecutor."""
       result = sum(i * i for i in range(n))
       return result

   async def main():
       # CPU tasks require a backend
       app = Flowrra.from_urls(backend='redis://localhost:6379/1')

       async with app:
           task_id = await app.submit(compute_heavy_operation, 1000000)
           result = await app.wait_for_result(task_id)
           print(f"Result: {result.result}")


Task Scheduling
---------------

Schedule tasks to run at specific times or intervals:

.. code-block:: python

   from flowrra import Flowrra
   import asyncio

   app = Flowrra.from_urls()

   # Create scheduler (automatically integrated with app)
   scheduler = app.create_scheduler()

   @app.task()
   async def cleanup_old_data():
       """Clean up old data."""
       print("Cleaning up...")
       return {"cleaned": 100}

   async def main():
       async with app:  # Automatically starts scheduler
           # Schedule with interval (every 30 minutes)
           await scheduler.schedule_interval(
               task_name="cleanup_old_data",
               interval=1800,  # seconds
               description="Every 30 minutes"
           )

           # Hourly at minute 0 (top of every hour)
           await scheduler.schedule_cron(
               task_name="cleanup_old_data",
               cron="0 * * * *",
               description="Hourly at :00"
           )

           # Daily at 2:30 AM
           await scheduler.schedule_cron(
               task_name="cleanup_old_data",
               cron="30 2 * * *",
               description="Daily at 2:30 AM"
           )

           # Weekly on Monday at 9:00 AM
           await scheduler.schedule_cron(
               task_name="cleanup_old_data",
               cron="0 9 * * 1",
               description="Weekly on Monday"
           )

           # Monthly on the 1st at midnight
           await scheduler.schedule_cron(
               task_name="cleanup_old_data",
               cron="0 0 1 * *",
               description="Monthly on 1st"
           )

           # Every weekday (Mon-Fri) at 6:00 PM
           await scheduler.schedule_cron(
               task_name="cleanup_old_data",
               cron="0 18 * * 1-5",
               description="Weekdays at 6 PM"
           )

           # Keep running to execute scheduled tasks
           await asyncio.Event().wait()

   asyncio.run(main())


Next Steps
----------

* Learn more about :doc:`guides/tasks`
* Set up :doc:`guides/scheduling`
* Explore :doc:`guides/web-ui`
* Check out :doc:`guides/backends` for production setups
