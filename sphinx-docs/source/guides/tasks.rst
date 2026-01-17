Working with Tasks
==================

Complete guide to defining, configuring, and executing tasks in Flowrra.


Defining Tasks
--------------

Tasks are defined using the ``@app.task()`` decorator:

.. code-block:: python

   from flowrra import Flowrra

   app = Flowrra.from_urls()

   @app.task()
   async def my_task(arg1: str, arg2: int):
       """Your task description."""
       # Task logic here
       return {"result": "success"}


Async vs Sync Tasks
--------------------

Async Tasks (I/O-bound)
~~~~~~~~~~~~~~~~~~~~~~~

Use ``async def`` for I/O-bound operations:

.. code-block:: python

   @app.task()
   async def fetch_api_data(url: str):
       async with httpx.AsyncClient() as client:
           response = await client.get(url)
           return response.json()


Sync Tasks (CPU-bound)
~~~~~~~~~~~~~~~~~~~~~~

Use regular ``def`` with ``cpu_bound=True`` for CPU-intensive work:

.. code-block:: python

   @app.task(cpu_bound=True)
   def process_large_file(file_path: str):
       # CPU-intensive operation
       with open(file_path) as f:
           data = f.read()
           # Process data
       return len(data)


Task Configuration
------------------

The ``@app.task()`` decorator accepts several configuration options:

.. code-block:: python

   @app.task(
       name="custom_task_name",      # Custom task identifier
       max_retries=3,                 # Number of retry attempts
       retry_delay=5.0,               # Initial retry delay in seconds
       priority=10,                   # Higher = executed first
       cpu_bound=False,               # Set to True for CPU-intensive tasks
       timeout=30.0                   # Task timeout in seconds
   )
   async def configured_task():
       pass


Retry Configuration
~~~~~~~~~~~~~~~~~~

Tasks can retry automatically on failure with exponential backoff:

.. code-block:: python

   @app.task(max_retries=5, retry_delay=2.0)
   async def may_fail():
       # Will retry with delays: 2s, 4s, 8s, 16s, 32s
       raise Exception("Temporary failure")


Submitting Tasks
----------------

Submit tasks for execution using ``app.submit()``:

.. code-block:: python

   async def main():
       async with app:
           # Submit task with arguments
           task_id = await app.submit(my_task, "arg1_value", 42)
           
           # Submit with keyword arguments
           task_id = await app.submit(
               my_task,
               arg1="value",
               arg2=42
           )


Retrieving Results
------------------

Wait for Task Completion
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async with app:
       task_id = await app.submit(my_task, "test", 123)
       
       # Wait for result with timeout
       result = await app.wait_for_result(task_id, timeout=10.0)
       
       if result.success:
           print(f"Result: {result.result}")
       else:
           print(f"Error: {result.error}")


Check Task Status
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get task status without waiting
   result = await app.get_result(task_id)
   
   if result:
       print(f"Status: {result.status}")
       print(f"Result: {result.result}")


Error Handling
--------------

Handle task failures gracefully:

.. code-block:: python

   @app.task(max_retries=3)
   async def risky_operation():
       try:
           # Risky code
           pass
       except SpecificError as e:
           # Handle specific errors
           raise  # Re-raise to trigger retry
       except Exception as e:
           # Log and return error state
           return {"error": str(e)}


Task Priority
-------------

Control execution order with priorities:

.. code-block:: python

   # High priority task (executed first)
   await app.submit(urgent_task, priority=100)
   
   # Normal priority task
   await app.submit(normal_task, priority=0)
   
   # Low priority task (executed last)
   await app.submit(background_task, priority=-10)


Best Practices
--------------

1. **Keep Tasks Idempotent** - Tasks should be safe to retry
2. **Use Type Hints** - Helps with IDE support and documentation
3. **Add Docstrings** - Document what your task does
4. **Handle Errors** - Don't let exceptions crash the worker
5. **Set Timeouts** - Prevent tasks from running forever
6. **Log Appropriately** - Use logging for debugging


Examples
--------

Email Sending Task
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @app.task(max_retries=3, retry_delay=10.0)
   async def send_email(to: str, subject: str, body: str):
       """Send email with retry logic."""
       async with aiosmtplib.SMTP() as smtp:
           await smtp.connect()
           await smtp.send_message(...)
           return {"sent": True, "to": to}


Data Processing Task
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @app.task(cpu_bound=True, timeout=300.0)
   def process_csv(file_path: str):
       """Process large CSV file."""
       import pandas as pd
       df = pd.read_csv(file_path)
       # Process data
       return {"rows_processed": len(df)}
