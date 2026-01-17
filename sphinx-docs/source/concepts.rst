Core Concepts
=============

Understanding Flowrra's architecture and key concepts.


Architecture Overview
---------------------

Flowrra is built on three main components:

1. **Task Queue** - Manages task submission and execution
2. **Scheduler** - Handles periodic and scheduled tasks (optional)
3. **Result Backend** - Stores task results for retrieval

.. code-block:: text

   ┌─────────────────────────────────────────────────┐
   │              Your Application                    │
   └────────────────┬────────────────────────────────┘
                    │
                    ▼
   ┌─────────────────────────────────────────────────┐
   │              Flowrra Core                        │
   │  ┌───────────────────────────────────────────┐  │
   │  │         Task Registry                     │  │
   │  └───────────────────────────────────────────┘  │
   │  ┌───────────────────────────────────────────┐  │
   │  │         Task Queue (asyncio.Queue)        │  │
   │  └───────────────────────────────────────────┘  │
   │  ┌───────────────────────────────────────────┐  │
   │  │         Executors (IO/CPU/Custom)         │  │
   │  └───────────────────────────────────────────┘  │
   └──────────────────┬──────────────────────────────┘
                      │
                      ▼
   ┌─────────────────────────────────────────────────┐
   │              Result Backend                      │
   │  (Memory / Redis / Custom)                       │
   └─────────────────────────────────────────────────┘


Tasks
-----

Tasks are the core unit of work in Flowrra. They can be either:

* **Async Tasks** (I/O-bound): Use ``async def`` for network requests, file I/O, etc.
* **Sync Tasks** (CPU-bound): Use regular ``def`` with ``cpu_bound=True`` for computation


Task Lifecycle
~~~~~~~~~~~~~~

1. **Registration** - Decorated functions are registered with the app
2. **Submission** - Tasks are submitted to the queue with arguments
3. **Queuing** - Tasks wait in priority queue
4. **Execution** - Executor picks up task and runs it
5. **Completion** - Result is stored in backend
6. **Retrieval** - Caller can wait for and retrieve results


Executors
---------

Flowrra supports three types of executors:

IOExecutor
~~~~~~~~~~

Default executor for async I/O-bound tasks:

* Uses asyncio concurrency
* Configurable max concurrent tasks
* Ideal for network requests, file I/O, database queries


CPUExecutor
~~~~~~~~~~~

ProcessPoolExecutor for CPU-bound tasks:

* Runs in separate processes
* Bypasses Python GIL
* Ideal for computation, data processing, image manipulation


CustomExecutor
~~~~~~~~~~~~~~

Create your own executor for specialized needs:

* Implement the ``Executor`` protocol
* Full control over task execution
* Can integrate with external systems


Result Backends
---------------

Result backends store task results for retrieval:

MemoryBackend (Default)
~~~~~~~~~~~~~~~~~~~~~~~

* In-process storage
* Fast but not persistent
* No external dependencies
* Ideal for development and single-process apps


RedisBackend
~~~~~~~~~~~~

* Distributed storage
* Persistent results
* Supports multiple workers
* Production-ready


Custom Backends
~~~~~~~~~~~~~~~

Implement the ``Backend`` protocol to create your own:

* Database storage (PostgreSQL, MongoDB, etc.)
* Cloud storage (S3, GCS, etc.)
* Message queues (RabbitMQ, Kafka, etc.)


Scheduler
---------

Optional component for running tasks periodically:

* **Cron schedules** - Traditional cron expressions
* **Interval schedules** - Run every N seconds
* **One-time schedules** - Run at a specific datetime
* **Persistent** - Survives restarts using SQLite/PostgreSQL/MySQL


Priority Queues
---------------

Tasks are executed based on priority:

* Higher priority (larger number) = executed first
* Default priority is 0
* Useful for urgent vs. background tasks


Retry Logic
-----------

Automatic retry with exponential backoff:

.. code-block:: python

   @app.task(max_retries=5, retry_delay=2.0)
   async def may_fail():
       # Task will retry up to 5 times
       # Delay: 2s, 4s, 8s, 16s, 32s
       pass


Context Managers
----------------

Flowrra uses async context managers for lifecycle management:

.. code-block:: python

   async with app:
       # App is started
       # Submit and execute tasks
       pass
       # App is gracefully stopped


Next Steps
----------

* Dive deeper into :doc:`guides/tasks`
* Learn about :doc:`guides/scheduling`
* Explore :doc:`guides/backends`
