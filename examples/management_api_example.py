"""Example demonstrating the Management API.

This shows how to use the pure Python management API to query
Flowrra application state without any web framework.
"""

import asyncio
from flowrra import Flowrra
from flowrra.management import FlowrraManager


# Create Flowrra app
app = Flowrra.from_urls()


# Register some tasks
@app.task()
async def send_email(to: str, subject: str):
    """Send an email (simulated)."""
    print(f"Sending email to {to}: {subject}")
    await asyncio.sleep(0.1)
    return f"Email sent to {to}"


@app.task(max_retries=5, retry_delay=2.0)
async def fetch_data(url: str):
    """Fetch data from URL (simulated)."""
    print(f"Fetching data from {url}")
    await asyncio.sleep(0.1)
    return {"status": "ok", "data": f"Data from {url}"}


async def main():
    """Demonstrate management API usage."""
    # Create manager
    manager = FlowrraManager(app)

    print("=" * 60)
    print("Flowrra Management API Example")
    print("=" * 60)

    # Check health before starting
    print("\n1. Health Check (Before Starting)")
    print("-" * 60)
    health = await manager.health_check()
    print(f"Healthy: {health['healthy']}")
    print(f"App: {health['components']['app']['message']}")

    # Start the app
    print("\n2. Starting Flowrra App...")
    print("-" * 60)
    await app.start()
    print("App started!")

    # Get system stats
    print("\n3. System Statistics")
    print("-" * 60)
    stats = await manager.get_stats()
    print(f"App Running: {stats['app']['running']}")
    print(f"IO Executor:")
    if stats['executors']['io']:
        print(f"  - Running: {stats['executors']['io']['running']}")
        print(f"  - Workers: {stats['executors']['io']['workers']}")
    print(f"Registered Tasks: {stats['tasks']['registered']}")
    print(f"Pending Tasks: {stats['tasks']['pending']}")

    # List registered tasks
    print("\n4. Registered Tasks")
    print("-" * 60)
    tasks = await manager.list_registered_tasks()
    for task in tasks:
        print(f"Task: {task['name']}")
        print(f"  - CPU Bound: {task['cpu_bound']}")
        print(f"  - Max Retries: {task['max_retries']}")
        print(f"  - Retry Delay: {task['retry_delay']}s")

    # Get specific task info
    print("\n5. Specific Task Info")
    print("-" * 60)
    task_info = await manager.get_task_info("send_email")
    if task_info:
        print(f"Task Name: {task_info['name']}")
        print(f"Module: {task_info['module']}")
        print(f"Qualified Name: {task_info['qualname']}")

    # Submit some tasks
    print("\n6. Submitting Tasks")
    print("-" * 60)
    task1 = app.registry.get("send_email")
    task2 = app.registry.get("fetch_data")

    task_id1 = await app.submit(task1, "user@example.com", "Hello World")
    task_id2 = await app.submit(task2, "https://api.example.com/data")

    print(f"Submitted send_email: {task_id1}")
    print(f"Submitted fetch_data: {task_id2}")

    # Wait for tasks to complete
    await asyncio.sleep(0.3)

    # Get task results
    print("\n7. Task Results")
    print("-" * 60)
    result1 = await manager.get_task_result(task_id1)
    if result1:
        print(f"Task {task_id1}:")
        print(f"  - Status: {result1['status']}")
        print(f"  - Result: {result1['result']}")

    result2 = await manager.get_task_result(task_id2)
    if result2:
        print(f"Task {task_id2}:")
        print(f"  - Status: {result2['status']}")
        print(f"  - Result: {result2['result']}")

    # Final health check
    print("\n8. Final Health Check")
    print("-" * 60)
    health = await manager.health_check()
    print(f"Healthy: {health['healthy']}")
    print(f"Timestamp: {health['timestamp']}")
    for component, status in health['components'].items():
        if status:
            print(f"{component}: {status['message']}")

    # Stop the app
    print("\n9. Stopping Flowrra App...")
    print("-" * 60)
    await app.stop()
    print("App stopped!")

    print("\n" + "=" * 60)
    print("Management API demonstration complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
