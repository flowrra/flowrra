"""Basic usage example demonstrating the unified Flowrra API.

This example shows:
1. Using Flowrra with from_urls() for simple setup
2. Registering I/O-bound tasks (async)
3. Registering CPU-bound tasks (sync)
4. Task execution with automatic routing
"""

import asyncio
from flowrra import Flowrra


async def main():
    """Main example demonstrating Flowrra usage."""
    print("Flowrra Basic Usage Example")
    print("=" * 60)

    # Create Flowrra app
    # Without broker/backend: Uses asyncio.PriorityQueue for I/O tasks
    # CPU tasks require explicit backend
    app = Flowrra.from_urls()

    # Register I/O-bound task (async function)
    @app.task()
    async def fetch_data(url: str):
        """Simulate fetching data from URL."""
        await asyncio.sleep(0.1)
        return f"Data from {url}"

    # Register another I/O-bound task
    @app.task(max_retries=3, retry_delay=1.0)
    async def send_email(to: str, subject: str):
        """Simulate sending an email."""
        await asyncio.sleep(0.1)
        print(f"  Email sent to {to}: {subject}")
        return {"sent": True, "to": to}

    # Start the application
    async with app:
        print("\n1. Submitting I/O-bound tasks...")

        # Submit I/O tasks
        task1 = await app.submit(fetch_data, "https://api.example.com")
        task2 = await app.submit(send_email, "alice@example.com", "Hello!")
        task3 = await app.submit(send_email, "bob@example.com", "Meeting Update")

        # Wait for results
        print("\n2. Waiting for results...")
        result1 = await app.wait_for_result(task1, timeout=5.0)
        result2 = await app.wait_for_result(task2, timeout=5.0)
        result3 = await app.wait_for_result(task3, timeout=5.0)

        print(f"\n3. Results:")
        print(f"   Task 1: {result1.result}")
        print(f"   Task 2: {result2.result}")
        print(f"   Task 3: {result3.result}")

    print("\n" + "=" * 60)
    print("✅ All tasks completed successfully!")


async def example_with_config():
    """Example using Config for structured configuration."""
    print("\n\nFlowrra with Config Example")
    print("=" * 60)

    from flowrra import Config, ExecutorConfig

    # Create config with custom executor settings
    config = Config(
        executor=ExecutorConfig(
            num_workers=4,
            max_retries=5,
            retry_delay=2.0
        )
    )

    app = Flowrra(config=config)

    @app.task()
    async def process_item(item_id: int):
        await asyncio.sleep(0.05)
        return f"Processed item {item_id}"

    async with app:
        print("\nProcessing 5 items concurrently...")

        # Submit multiple tasks
        task_ids = []
        for i in range(1, 6):
            task_id = await app.submit(process_item, i)
            task_ids.append(task_id)

        # Wait for all
        print("\nResults:")
        for task_id in task_ids:
            result = await app.wait_for_result(task_id, timeout=2.0)
            print(f"  {result.result}")

    print("\n" + "=" * 60)
    print("✅ Config example completed!")


async def example_with_broker():
    """Example demonstrating Redis broker for distributed task queue."""
    print("\n\nFlowrra with Redis Broker Example")
    print("=" * 60)
    print("Note: Requires Redis server running at localhost:6379")

    try:
        # Use Redis broker for distributed task queueing
        app = Flowrra.from_urls(
            broker='redis://localhost:6379/0',
            backend='redis://localhost:6379/1'
        )

        @app.task()
        async def distributed_task(task_num: int):
            await asyncio.sleep(0.1)
            return f"Completed task {task_num} via Redis broker"

        async with app:
            print("\nSubmitting tasks to Redis broker...")

            task_ids = []
            for i in range(1, 4):
                task_id = await app.submit(distributed_task, i)
                task_ids.append(task_id)
                print(f"  Submitted task {i}")

            print("\nWorkers pulling from Redis queue...")
            for task_id in task_ids:
                result = await app.wait_for_result(task_id, timeout=5.0)
                print(f"  {result.result}")

        print("\n✓ Redis broker example completed successfully")

    except Exception as e:
        print(f"\n✗ Redis broker example failed: {e}")
        print("  Make sure Redis is running: redis-server")
        print("  Or install Redis: brew install redis (macOS) / apt install redis (Ubuntu)")


async def example_with_cpu_bound():
    """Example demonstrating CPU-bound tasks with CPUExecutor."""
    print("\n\nFlowrra with CPU-bound Task Example")
    print("=" * 60)
    print("Note: CPU-bound tasks require explicit backend for cross-process result sharing")

    try:
        # CPU tasks require explicit backend (Redis)
        app = Flowrra.from_urls(
            backend='redis://localhost:6379/0'
        )

        # CPU-bound task (sync function, not async!)
        @app.task(cpu_bound=True)
        def heavy_computation(n: int):
            """CPU-intensive computation - runs in separate process."""
            result = sum(i ** 2 for i in range(n))
            return result

        # Another CPU-bound task
        @app.task(cpu_bound=True)
        def factorial(n: int):
            """Calculate factorial - CPU intensive."""
            if n == 0 or n == 1:
                return 1
            result = 1
            for i in range(2, n + 1):
                result *= i
            return result

        async with app:
            print("\nSubmitting CPU-bound tasks...")

            # Submit multiple CPU tasks
            task1 = await app.submit(heavy_computation, 1000000)
            task2 = await app.submit(factorial, 20)
            task3 = await app.submit(heavy_computation, 500000)

            print("  Submitted 3 CPU-intensive tasks")
            print("  These run in separate processes using CPUExecutor")

            # Wait for results
            print("\nWaiting for results...")
            result1 = await app.wait_for_result(task1, timeout=10.0)
            result2 = await app.wait_for_result(task2, timeout=10.0)
            result3 = await app.wait_for_result(task3, timeout=10.0)

            print(f"\n  Task 1 (sum of squares to 1M): {result1.result}")
            print(f"  Task 2 (factorial of 20): {result2.result}")
            print(f"  Task 3 (sum of squares to 500K): {result3.result}")

        print("\n✓ CPU-bound task example completed successfully")

    except ValueError as e:
        print(f"\n✗ CPU-bound task example failed: {e}")
        print("  CPU-bound tasks require explicit backend configuration")
    except Exception as e:
        print(f"\n✗ CPU-bound task example failed: {e}")
        print("  Make sure Redis is running: redis-server")
        print("  Or install Redis: brew install redis (macOS) / apt install redis (Ubuntu)")


if __name__ == "__main__":
    # Run basic example
    asyncio.run(main())

    # Run config example
    asyncio.run(example_with_config())

    # Run broker example (will fail gracefully if Redis not available)
    asyncio.run(example_with_broker())

    # Run CPU-bound example (will fail gracefully if Redis not available)
    asyncio.run(example_with_cpu_bound())
