import asyncio

from flowrra import AsyncTaskExecutor

async def main():
    executor = AsyncTaskExecutor(num_workers=3)

    @executor.task(max_retries=2, retry_delay=1)
    async def send_email(to: str, subject: str):
        """Simulate sending an email."""
        await asyncio.sleep(1)
        print(f"Email sent to {to}: {subject}")
        return {"sent": True, "to": to}
    
    @executor.task()
    async def process_data(numbers: list[int]):
        """Process some data."""
        await asyncio.sleep(2)
        result = sum(numbers) * 2
        print(f"Processed data: {result}")
        return result

    @executor.task(max_retries=3)
    async def flaky_task():
        """Demonstrates retry behavior."""
        import random
        await asyncio.sleep(0.5)
        if random.random() < 0.6:
            raise RuntimeError("Random failure!")
        return "Success!"
    
    # Use context manager for clean startup/shutdown
    async with executor:
        task_ids = [
            await executor.submit(send_email, "alice@example.com", "Hello!"),
            await executor.submit(send_email, "bob@example.com", "Meeting"),
            await executor.submit(process_data, [1, 2, 3, 4, 5]),
            await executor.submit(flaky_task, priority=1),  # Higher priority
        ]

    # Wait for all results
    print("\n" + "="*50)
    print("Results")
    print("="*50)
    
    for task_id in task_ids:
        result = await executor.wait_for_result(task_id, timeout=10.0)
        print(f"\n[{task_id[:8]}]")
        print(f"  Status:  {result.status.value}")
        print(f"  Result:  {result.result}")
        print(f"  Retries: {result.retries}")
        if result.error:
            print(f"  Error:   {result.error}")
    
    print("\n✅ All tasks completed!")