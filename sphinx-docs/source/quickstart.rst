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

For CPU-intensive operations, use the ``executor`` parameter:

.. code-block:: python

   @app.task(executor="cpu")
   def compute_heavy_operation(n: int):
       """CPU-intensive task using ProcessPoolExecutor."""
       result = sum(i * i for i in range(n))
       return result

   async def main():
       async with app:
           task_id = await app.submit(compute_heavy_operation, 1000000)
           result = await app.wait_for_result(task_id)
           print(f"Result: {result.result}")


Task Scheduling
---------------

Schedule tasks to run at specific times or intervals:

.. code-block:: python

   from flowrra import Flowrra

   app = Flowrra.from_urls(
       scheduler_url="sqlite:///scheduler.db"
   )

   @app.task()
   async def cleanup_old_data():
       """Clean up old data."""
       print("Cleaning up...")
       return {"cleaned": 100}

   async def main():
       async with app:
           # Schedule task to run every hour
           await app.schedule_interval(
               "cleanup_old_data",
               interval=3600,  # seconds
               task_name="cleanup_old_data"
           )
           
           # Schedule with cron expression
           await app.schedule_cron(
               "0 0 * * *",  # Run daily at midnight
               task_name="cleanup_old_data"
           )


Next Steps
----------

* Learn more about :doc:`guides/tasks`
* Set up :doc:`guides/scheduling`
* Explore :doc:`guides/web-ui`
* Check out :doc:`guides/backends` for production setups
