Web UI
======

Flowrra provides a built-in web dashboard for monitoring and managing tasks, schedules, and system statistics. The UI integrates seamlessly with popular Python web frameworks.

Overview
--------

The Web UI provides:

* **Dashboard**: System statistics, recent failed tasks, and active schedules
* **Tasks**: View registered tasks and execution history with status filtering
* **Schedules**: Manage cron and interval-based task schedules
* **REST API**: JSON endpoints for programmatic access

Framework Integration
---------------------

Flowrra supports integration with FastAPI, Flask, Quart, and Django. Choose the integration that matches your web framework.

FastAPI Integration
^^^^^^^^^^^^^^^^^^^

For FastAPI applications, use ``create_router()``:

.. code-block:: python

   from contextlib import asynccontextmanager
   from fastapi import FastAPI
   from flowrra import Flowrra
   from flowrra.ui.fastapi import create_router

   # Create your Flowrra app
   flowrra = Flowrra.from_urls(
       broker='redis://localhost:6379/0',
       backend='redis://localhost:6379/1'
   )

   # Register tasks
   @flowrra.task()
   async def send_email(to: str, subject: str):
       """Send an email asynchronously."""
       await asyncio.sleep(2)  # Simulate email sending
       return {"status": "sent", "to": to}

   @flowrra.task()
   async def daily_report():
       """Generate daily report."""
       print("Generating daily report...")
       return {"status": "completed"}

   # Create scheduler and schedule tasks
   scheduler = flowrra.create_scheduler()

   # Lifespan context manager for startup/shutdown
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Schedule daily report at 9 AM (before starting)
       await scheduler.schedule_cron(
           task_name="daily_report",
           cron="0 9 * * *",
           description="Daily report at 9 AM"
       )

       # Startup
       await flowrra.start()
       yield
       # Shutdown
       await flowrra.stop()

   # Create FastAPI app with lifespan
   app = FastAPI(lifespan=lifespan)

   # Include Flowrra UI router
   app.include_router(
       create_router(flowrra),
       prefix="/flowrra",
       tags=["flowrra"]
   )

   # Your other FastAPI routes
   @app.get("/")
   async def root():
       return {"message": "Hello World"}

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)

Access the UI at: ``http://localhost:8000/flowrra``

Flask/Quart Integration
^^^^^^^^^^^^^^^^^^^^^^^

For Flask or Quart applications, use ``create_blueprint()``.

**Quart (Recommended for async support):**

.. code-block:: python

   from quart import Quart
   from flowrra import Flowrra
   from flowrra.ui.flask import create_blueprint

   # Create your Flowrra app
   flowrra = Flowrra.from_urls(
       broker='redis://localhost:6379/0',
       backend='redis://localhost:6379/1'
   )

   # Register tasks
   @flowrra.task()
   async def send_email(to: str, subject: str):
       """Send an email asynchronously."""
       await asyncio.sleep(2)
       return {"status": "sent", "to": to}

   @flowrra.task()
   async def cleanup_old_data():
       """Clean up old data."""
       print("Cleaning up old data...")
       return {"cleaned": 100}

   # Create scheduler and schedule tasks
   scheduler = flowrra.create_scheduler()

   # Create Quart app and register Flowrra blueprint
   app = Quart(__name__)

   app.register_blueprint(
       create_blueprint(flowrra),
       url_prefix="/flowrra"
   )

   # Lifecycle events
   @app.before_serving
   async def startup():
       # Schedule cleanup task to run daily at midnight
       await scheduler.schedule_cron(
           task_name="cleanup_old_data",
           cron="0 0 * * *",
           description="Daily cleanup at midnight"
       )
       await flowrra.start()

   @app.after_serving
   async def shutdown():
       await flowrra.stop()

   # Your other Quart routes
   @app.route("/")
   async def root():
       return {"message": "Hello World"}

   if __name__ == "__main__":
       app.run(host="0.0.0.0", port=8000)

**Flask (Traditional):**

.. code-block:: python

   from flask import Flask
   from flowrra import Flowrra
   from flowrra.ui.flask import create_blueprint
   import threading
   import asyncio

   # Create your Flowrra app
   flowrra = Flowrra.from_urls(
       broker='redis://localhost:6379/0',
       backend='redis://localhost:6379/1'
   )

   # Register tasks
   @flowrra.task()
   async def send_email(to: str, subject: str):
       """Send an email asynchronously."""
       await asyncio.sleep(2)
       return {"status": "sent", "to": to}

   @flowrra.task()
   async def weekly_summary():
       """Generate weekly summary."""
       print("Generating weekly summary...")
       return {"status": "completed"}

   # Create scheduler and schedule tasks
   scheduler = flowrra.create_scheduler()

   async def setup_schedules():
       # Schedule weekly summary every Monday at 9 AM
       await scheduler.schedule_cron(
           task_name="weekly_summary",
           cron="0 9 * * 1",
           description="Weekly summary on Monday"
       )

   # Create Flask app and register Flowrra blueprint
   app = Flask(__name__)

   app.register_blueprint(
       create_blueprint(flowrra),
       url_prefix="/flowrra"
   )

   # Your other Flask routes
   @app.route("/")
   def root():
       return {"message": "Hello World"}

   # Start Flowrra in background thread
   async def run_flowrra_async():
       await setup_schedules()
       await flowrra.run()

   def run_flowrra():
       asyncio.run(run_flowrra_async())

   if __name__ == "__main__":
       thread = threading.Thread(target=run_flowrra, daemon=True)
       thread.start()
       app.run(host="0.0.0.0", port=8000)

Access the UI at: ``http://localhost:8000/flowrra``

Django Integration
^^^^^^^^^^^^^^^^^^

For Django applications, use ``get_urls()``:

**1. Create your Flowrra app (e.g., in myapp/flowrra_app.py):**

.. code-block:: python

   # myapp/flowrra_app.py
   from flowrra import Flowrra

   # Create Flowrra app
   flowrra = Flowrra.from_urls(
       broker='redis://localhost:6379/0',
       backend='redis://localhost:6379/1'
   )

   # Register tasks
   @flowrra.task()
   async def send_email(to: str, subject: str):
       """Send an email asynchronously."""
       import asyncio
       await asyncio.sleep(2)
       return {"status": "sent", "to": to}

   @flowrra.task()
   async def monthly_backup():
       """Perform monthly backup."""
       print("Running monthly backup...")
       return {"status": "backup_complete"}

   # Create scheduler
   scheduler = flowrra.create_scheduler()

**2. Add to your Django project's urls.py:**

.. code-block:: python

   # myproject/urls.py
   from django.contrib import admin
   from django.urls import path, include
   from flowrra.ui.django import get_urls
   from myapp.flowrra_app import flowrra

   urlpatterns = [
       path('admin/', admin.site.urls),
       # Your other Django URLs
       path('flowrra/', include(get_urls(flowrra))),
   ]

**3. Start Flowrra in your AppConfig:**

.. code-block:: python

   # myapp/apps.py
   from django.apps import AppConfig
   import asyncio

   class MyAppConfig(AppConfig):
       default_auto_field = 'django.db.models.BigAutoField'
       name = 'myapp'

       def ready(self):
           from myapp.flowrra_app import flowrra, scheduler

           # Schedule tasks before starting
           async def setup():
               # Schedule monthly backup on 1st day at midnight
               await scheduler.schedule_cron(
                   task_name="monthly_backup",
                   cron="0 0 1 * *",
                   description="Monthly backup on 1st"
               )
               # Start Flowrra when Django starts
               await flowrra.start()

           asyncio.create_task(setup())

Access the UI at: ``http://localhost:8000/flowrra/``

UI Features
-----------

Dashboard Page
^^^^^^^^^^^^^^

The dashboard provides an overview of your Flowrra system:

* **System Statistics**:

  * Total tasks executed
  * Success/failure rates
  * Active workers count
  * Queue size

* **Recent Failed Tasks**: Quick access to tasks that need attention
* **Active Schedules**: Overview of upcoming scheduled tasks

Tasks Page
^^^^^^^^^^

View and filter task execution history:

* **Filter by status**: All, Pending, Running, Success, Failed
* **Registered Tasks**: View all tasks with their configuration (type, retries, retry delay)
* **Execution History**: Complete task history with timestamps and duration
* **Error Details**: Expandable error messages for failed tasks
* **Status Badges**: Color-coded status indicators

Schedules Page
^^^^^^^^^^^^^^

Manage scheduled tasks:

* **View all schedules**: Cron and interval-based schedules
* **Enable/disable schedules**: Toggle schedules on/off
* **Next execution time**: See when each schedule will run next
* **Execution statistics**: Track schedule performance
* **Create new schedules**: Via REST API

REST API Endpoints
------------------

All integrations expose the following JSON API endpoints:

System Endpoints
^^^^^^^^^^^^^^^^

* ``GET /flowrra/api/health`` - Health check
* ``GET /flowrra/api/stats`` - System statistics

Task Endpoints
^^^^^^^^^^^^^^

* ``GET /flowrra/api/tasks`` - List registered tasks
* ``GET /flowrra/api/tasks/{name}`` - Get specific task info

Schedule Endpoints
^^^^^^^^^^^^^^^^^^

* ``GET /flowrra/api/schedules`` - List all schedules
* ``GET /flowrra/api/schedules?enabled_only=true`` - List only enabled schedules
* ``GET /flowrra/api/schedules/{id}`` - Get specific schedule
* ``POST /flowrra/api/schedules/cron`` - Create cron schedule
* ``PUT /flowrra/api/schedules/{id}/enable`` - Enable schedule
* ``PUT /flowrra/api/schedules/{id}/disable`` - Disable schedule
* ``DELETE /flowrra/api/schedules/{id}`` - Delete schedule

Example API Usage
^^^^^^^^^^^^^^^^^

**Get system statistics:**

.. code-block:: python

   import httpx

   response = httpx.get("http://localhost:8000/flowrra/api/stats")
   stats = response.json()
   print(f"Total tasks: {stats['total_tasks']}")
   print(f"Success rate: {stats['success_rate']}%")

**List registered tasks:**

.. code-block:: python

   response = httpx.get("http://localhost:8000/flowrra/api/tasks")
   tasks = response.json()

   for task in tasks:
       print(f"{task['name']}: {task['type']}")

**Create a cron schedule:**

.. code-block:: python

   response = httpx.post(
       "http://localhost:8000/flowrra/api/schedules/cron",
       json={
           "task_name": "send_email",
           "cron": "0 9 * * 1",  # Every Monday at 9 AM
           "description": "Weekly email report",
           "args": ["admin@example.com", "Weekly Report"],
           "enabled": True,
           "priority": 5
       }
   )
   schedule = response.json()
   print(f"Created schedule: {schedule['schedule_id']}")

**Enable/disable a schedule:**

.. code-block:: python

   # Disable
   httpx.put(f"http://localhost:8000/flowrra/api/schedules/{schedule_id}/disable")

   # Enable
   httpx.put(f"http://localhost:8000/flowrra/api/schedules/{schedule_id}/enable")

**Delete a schedule:**

.. code-block:: python

   httpx.delete(f"http://localhost:8000/flowrra/api/schedules/{schedule_id}")

Customization
-------------

Custom Mount Path
^^^^^^^^^^^^^^^^^

You can mount the UI at any path:

.. code-block:: python

   # FastAPI
   app.include_router(
       create_router(flowrra),
       prefix="/admin/tasks",
       tags=["admin"]
   )

   # Flask/Quart
   app.register_blueprint(
       create_blueprint(flowrra),
       url_prefix="/admin/tasks"
   )

   # Django
   path('admin/tasks/', include(get_urls(flowrra)))

Then access at: ``http://localhost:8000/admin/tasks/``

Production Deployment
---------------------

Best Practices
^^^^^^^^^^^^^^

For production deployments:

1. **Use Redis** for both broker and backend:

   .. code-block:: python

      flowrra = Flowrra.from_urls(
          broker='redis://localhost:6379/0',
          backend='redis://localhost:6379/1'
      )

2. **Enable authentication** on your web framework
3. **Use reverse proxy** (nginx, Traefik) for HTTPS
4. **Monitor resources** via the dashboard
5. **Set up alerting** based on failed task metrics

Authentication Example (FastAPI)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Protect the Flowrra UI with authentication:

.. code-block:: python

   from contextlib import asynccontextmanager
   from fastapi import FastAPI, Depends, HTTPException, status
   from fastapi.security import HTTPBasic, HTTPBasicCredentials
   from flowrra import Flowrra
   from flowrra.ui.fastapi import create_router
   import secrets

   flowrra = Flowrra.from_urls()
   security = HTTPBasic()

   def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
       """Verify username and password."""
       correct_username = secrets.compare_digest(credentials.username, "admin")
       correct_password = secrets.compare_digest(credentials.password, "secure_password")

       if not (correct_username and correct_password):
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Invalid credentials",
               headers={"WWW-Authenticate": "Basic"},
           )
       return credentials.username

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       await flowrra.start()
       yield
       await flowrra.stop()

   app = FastAPI(lifespan=lifespan)
   flowrra_router = create_router(flowrra)

   # Add authentication dependency to all routes
   flowrra_router.dependencies = [Depends(verify_credentials)]

   app.include_router(
       flowrra_router,
       prefix="/flowrra"
   )

Nginx Reverse Proxy
^^^^^^^^^^^^^^^^^^^

Example nginx configuration for HTTPS:

.. code-block:: nginx

   server {
       listen 443 ssl;
       server_name example.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location /flowrra {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
       }
   }

See Also
--------

* :doc:`../api/flowrra.ui` - UI API Reference
* :doc:`scheduling` - Task Scheduling Guide
* :doc:`tasks` - Task Configuration Guide
* :doc:`backends` - Backend Configuration
