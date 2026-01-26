"""Quart UI Example - Flowrra Web Interface with Quart

This example demonstrates how to mount the Flowrra UI into a Quart application.
Quart is an async version of Flask with a compatible API.

Requirements:
    pip install flowrra[ui-flask]  # Includes Quart

Usage:
    python examples/quart_ui_example.py

Then visit: http://localhost:8000/flowrra/
"""

import asyncio
from datetime import datetime
from quart import Quart

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


# Create Quart app
app = Quart(__name__)


# Mount Flowrra UI
try:
    from flowrra.ui.flask import create_blueprint

    flowrra_blueprint = create_blueprint(flowrra)
    app.register_blueprint(
        flowrra_blueprint,
        url_prefix="/flowrra",
    )
    print("✅ Flowrra UI mounted at /flowrra/")
except ImportError:
    print("⚠️  Flask/Quart UI adapter not available. Install with: pip install flowrra[ui-flask]")


# Add some API endpoints to submit tasks
@app.route("/api/send-email", methods=["POST"])
async def api_send_email():
    """Submit an email task."""
    from quart import request
    data = await request.get_json()
    task_id = await send_email.submit(data["to"], data["subject"], data["body"])
    return {"task_id": task_id, "status": "submitted"}


@app.route("/api/fetch-data", methods=["POST"])
async def api_fetch_data():
    """Submit a data fetching task."""
    from quart import request
    data = await request.get_json()
    task_id = await fetch_data.submit(data["url"])
    return {"task_id": task_id, "status": "submitted"}


@app.route("/api/process-order", methods=["POST"])
async def api_process_order():
    """Submit an order processing task."""
    from quart import request
    data = await request.get_json()
    task_id = await process_order.submit(data["order_id"], data["items"])
    return {"task_id": task_id, "status": "submitted"}


@app.route("/")
async def root():
    """Root endpoint with links."""
    return {
        "message": "Flowrra Quart Example",
        "links": {
            "flowrra_ui": "/flowrra/",
            "flowrra_api": "/flowrra/api/stats",
        },
    }


# Lifecycle events
@app.before_serving
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


@app.after_serving
async def shutdown():
    """Stop Flowrra on application shutdown."""
    print("\n🛑 Stopping Flowrra...")
    await flowrra.stop()
    print("✅ Flowrra stopped")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════╗
║   Flowrra Quart UI Example                     ║
╚════════════════════════════════════════════════╝

🌐 Starting Quart server...

📊 Flowrra UI available at:
   http://localhost:8000/flowrra/

🔧 API Endpoints:
   POST /api/send-email
   POST /api/fetch-data
   POST /api/process-order

Press Ctrl+C to stop the server
    """)

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,
    )
