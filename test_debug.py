"""Debug test to isolate the issue."""
import asyncio
import logging
from flowrra import AsyncTaskExecutor

logging.basicConfig(level=logging.DEBUG)

async def main():
    print("Creating executor...")
    executor = AsyncTaskExecutor(num_workers=2)

    @executor.task()
    async def my_task(x: int) -> int:
        print(f"Task executing with x={x}")
        await asyncio.sleep(0.1)
        print(f"Task completed")
        return x * 2

    print("Starting executor...")
    async with executor:
        print("Executor started")
        print("Submitting task...")
        task_id = await executor.submit(my_task, 10)
        print(f"Task submitted: {task_id}")

        # Wait a bit for task to execute
        await asyncio.sleep(0.5)
        print("Exiting context manager...")

    print("Context manager exited")

if __name__ == "__main__":
    asyncio.run(main())
