Flowrra Documentation
=====================

Lightweight async task queue built on pure Python asyncio. A Celery-inspired background job executor with zero dependencies, featuring retries, priority queues, and pluggable backends.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart
   concepts

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   guides/tasks
   guides/scheduling
   guides/web-ui
   guides/backends
   guides/executors

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources

   changelog
   contributing
   license


Features
--------

* **Zero Dependencies** - Built on pure Python 3.11+ asyncio (only aiosqlite required for scheduler)
* **Simple API** - Decorator-based task registration, just like Celery
* **Async First** - Native async/await support for I/O-bound tasks
* **CPU-Bound Support** - ProcessPoolExecutor integration for compute-heavy tasks
* **Task Scheduling** - Celery Beat-like persistent scheduling with cron, intervals, and one-time tasks
* **Web UI** - Built-in monitoring dashboard for FastAPI, Flask/Quart, and Django
* **Automatic Retries** - Configurable retry logic with exponential backoff
* **Priority Queues** - Control task execution order
* **Pluggable Backends** - Extensible result storage (in-memory included)
* **Multiple Databases** - SQLite, PostgreSQL, and MySQL support for scheduler
* **Type Safe** - Full type hints for better IDE support


Quick Example
-------------

.. code-block:: python

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


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
