"""Django UI Example - Flowrra Web Interface with Django

This example demonstrates how to mount the Flowrra UI into a Django application.

Requirements:
    pip install flowrra[ui-django]  # Includes Django

Usage:
    python examples/django_ui_example.py

Then visit: http://localhost:8000/flowrra/

Note: This is a minimal Django setup for demonstration. For production,
      use proper Django project structure (manage.py, settings.py, etc.)
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Configure Django settings before imports
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='django-insecure-example-key-change-in-production',
        ROOT_URLCONF=__name__,  # Use this module as the URL config
        ALLOWED_HOSTS=['*'],
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.staticfiles',
        ],
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.common.CommonMiddleware',
        ],
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.request',
                ],
            },
        }],
        STATIC_URL='/static/',
    )
    django.setup()

from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from flowrra import Flowrra, Config, ExecutorConfig

# Create Flowrra application
config = Config(executor=ExecutorConfig(io_workers=4))
flowrra = Flowrra(config=config)


# Define some example tasks
@flowrra.task()
async def send_email(to: str, subject: str, body: str):
    """Simulate sending an email."""
    print(f"📧 Sending email to {to}: {subject}")
    await asyncio.sleep(1)  # Simulate API call
    return {"sent": True, "to": to, "timestamp": datetime.now().isoformat()}


@flowrra.task(max_retries=3, retry_delay=5.0)
async def fetch_data(url: str):
    """Simulate fetching data from an API."""
    print(f"🌐 Fetching data from {url}")
    await asyncio.sleep(0.5)
    return {"url": url, "data": "sample data", "timestamp": datetime.now().isoformat()}


@flowrra.task()
async def process_order(order_id: int, items: list):
    """Simulate processing an order."""
    print(f"🛒 Processing order {order_id} with {len(items)} items")
    await asyncio.sleep(2)
    return {
        "order_id": order_id,
        "status": "processed",
        "total_items": len(items),
        "timestamp": datetime.now().isoformat(),
    }


@flowrra.task(cpu_bound=True)
def calculate_stats(numbers: list):
    """CPU-bound task to calculate statistics (requires CPUExecutor)."""
    import statistics

    print(f"📊 Calculating stats for {len(numbers)} numbers")
    return {
        "count": len(numbers),
        "mean": statistics.mean(numbers),
        "median": statistics.median(numbers),
        "stdev": statistics.stdev(numbers) if len(numbers) > 1 else 0,
    }


# API endpoints to submit tasks
@csrf_exempt
@require_http_methods(["POST"])
def api_send_email(request):
    """Submit an email task."""
    data = json.loads(request.body)

    # Use asyncio.run since Django views are sync
    task_id = asyncio.run(send_email.submit(data["to"], data["subject"], data["body"]))
    return JsonResponse({"task_id": task_id, "status": "submitted"})


@csrf_exempt
@require_http_methods(["POST"])
def api_fetch_data(request):
    """Submit a data fetching task."""
    data = json.loads(request.body)
    task_id = asyncio.run(fetch_data.submit(data["url"]))
    return JsonResponse({"task_id": task_id, "status": "submitted"})


@csrf_exempt
@require_http_methods(["POST"])
def api_process_order(request):
    """Submit an order processing task."""
    data = json.loads(request.body)
    task_id = asyncio.run(process_order.submit(data["order_id"], data["items"]))
    return JsonResponse({"task_id": task_id, "status": "submitted"})


def root(request):
    """Root endpoint with links."""
    return JsonResponse({
        "message": "Flowrra Django Example",
        "links": {
            "flowrra_ui": "/flowrra/",
            "flowrra_api": "/flowrra/api/stats",
        },
    })


# URL Configuration
try:
    from flowrra.ui.django import get_urls

    urlpatterns = [
        path('', root),
        path('api/send-email/', api_send_email),
        path('api/fetch-data/', api_fetch_data),
        path('api/process-order/', api_process_order),
        path('flowrra/', include(get_urls(flowrra))),
    ]
    print("✅ Flowrra UI mounted at /flowrra/")
except ImportError:
    print("⚠️  Django UI adapter not available. Install with: pip install flowrra[ui-django]")
    urlpatterns = [
        path('', root),
    ]


async def startup():
    """Start Flowrra on application startup."""
    print("🚀 Starting Flowrra...")
    await flowrra.start()
    print("✅ Flowrra started")

    # Optionally create scheduler
    try:
        scheduler = flowrra.create_scheduler()
        print("📅 Scheduler created")

        # Schedule some tasks
        await scheduler.schedule_cron(
            task_name="fetch_data",
            cron="*/5 * * * *",  # Every 5 minutes
            args=("https://api.example.com/data",),
            description="Fetch data every 5 minutes",
        )
        print("✅ Scheduled task: fetch_data")

    except Exception as e:
        print(f"⚠️  Could not create scheduler: {e}")

    # Submit some initial tasks
    print("\n📋 Submitting initial tasks...")
    await send_email.submit("user@example.com", "Welcome", "Welcome to Flowrra!")
    await fetch_data.submit("https://api.example.com/users")
    await process_order.submit(12345, ["item1", "item2", "item3"])
    print("✅ Initial tasks submitted\n")


async def shutdown():
    """Stop Flowrra on application shutdown."""
    print("\n🛑 Stopping Flowrra...")
    await flowrra.stop()
    print("✅ Flowrra stopped")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════╗
║   Flowrra Django UI Example                    ║
╚════════════════════════════════════════════════╝

🌐 Starting Django development server...

📊 Flowrra UI available at:
   http://localhost:8000/flowrra/

🔧 API Endpoints:
   POST /api/send-email/
   POST /api/fetch-data/
   POST /api/process-order/

Press Ctrl+C to stop the server
    """)

    # Start Flowrra
    asyncio.run(startup())

    # Run Django development server
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line([
            'manage.py',
            'runserver',
            '0.0.0.0:8000',
            '--noreload',  # Disable auto-reload to prevent double startup
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        asyncio.run(shutdown())
        sys.exit(0)
