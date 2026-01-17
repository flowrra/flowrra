"""Tests for WebSocket EventBus enhancements."""

import asyncio
import pytest
from flowrra.events import EventBus


class TestEventBus:
    """Test the enhanced EventBus implementation."""

    @pytest.mark.asyncio
    async def test_subscribe_and_emit(self):
        """Test basic subscribe and emit functionality."""
        bus = EventBus()
        received = []

        async def subscriber(event: dict):
            received.append(event)

        bus.subscribe(subscriber)

        await bus.emit({"type": "test", "data": "hello"})

        assert len(received) == 1
        assert received[0]["type"] == "test"
        assert received[0]["data"] == "hello"

    @pytest.mark.asyncio
    async def test_async_subscribe(self):
        """Test async-safe subscription."""
        bus = EventBus()
        received = []

        async def subscriber(event: dict):
            received.append(event)

        await bus.async_subscribe(subscriber)

        await bus.emit({"type": "test"})

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribe functionality."""
        bus = EventBus()
        received = []

        async def subscriber(event: dict):
            received.append(event)

        await bus.async_subscribe(subscriber)
        await bus.emit({"type": "test1"})

        await bus.unsubscribe(subscriber)
        await bus.emit({"type": "test2"})

        # Should only receive the first event
        assert len(received) == 1
        assert received[0]["type"] == "test1"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers receive events concurrently."""
        bus = EventBus()
        received1 = []
        received2 = []
        received3 = []

        async def subscriber1(event: dict):
            await asyncio.sleep(0.01)  # Simulate async work
            received1.append(event)

        async def subscriber2(event: dict):
            received2.append(event)

        async def subscriber3(event: dict):
            await asyncio.sleep(0.02)
            received3.append(event)

        bus.subscribe(subscriber1)
        bus.subscribe(subscriber2)
        bus.subscribe(subscriber3)

        await bus.emit({"type": "broadcast"})

        # All subscribers should receive the event
        assert len(received1) == 1
        assert len(received2) == 1
        assert len(received3) == 1

    @pytest.mark.asyncio
    async def test_error_isolation(self):
        """Test that one subscriber's error doesn't affect others."""
        bus = EventBus()
        received_good = []

        async def bad_subscriber(event: dict):
            raise RuntimeError("Intentional error")

        async def good_subscriber(event: dict):
            received_good.append(event)

        bus.subscribe(bad_subscriber)
        bus.subscribe(good_subscriber)

        # Should not raise, error is isolated
        await bus.emit({"type": "test"})

        # Good subscriber should still receive the event
        assert len(received_good) == 1

    @pytest.mark.asyncio
    async def test_concurrent_subscription_modification(self):
        """Test thread-safe subscription during emission."""
        bus = EventBus()
        received = []

        async def subscriber(event: dict):
            received.append(event)

        # Subscribe initially
        bus.subscribe(subscriber)

        # Emit while also subscribing new subscribers
        async def emit_task():
            for i in range(5):
                await bus.emit({"type": "test", "value": i})
                await asyncio.sleep(0.01)

        async def subscribe_task():
            for _ in range(3):
                await asyncio.sleep(0.015)
                async def new_sub(event: dict):
                    received.append({"new": event})
                await bus.async_subscribe(new_sub)

        # Run concurrently
        await asyncio.gather(emit_task(), subscribe_task())

        # Should receive events without errors
        assert len(received) > 0

    @pytest.mark.asyncio
    async def test_empty_subscriber_list(self):
        """Test emission with no subscribers."""
        bus = EventBus()

        # Should not raise
        await bus.emit({"type": "test"})

    @pytest.mark.asyncio
    async def test_task_update_event_format(self):
        """Test emission of task update events (real use case)."""
        bus = EventBus()
        received = []

        async def subscriber(event: dict):
            received.append(event)

        bus.subscribe(subscriber)

        # Emit task update in the format used by executors
        await bus.emit({
            'type': 'task.update',
            'task': {
                'task_id': '123',
                'status': 'running',
                'task_name': 'test_task',
            }
        })

        assert len(received) == 1
        assert received[0]['type'] == 'task.update'
        assert received[0]['task']['task_id'] == '123'
        assert received[0]['task']['status'] == 'running'
