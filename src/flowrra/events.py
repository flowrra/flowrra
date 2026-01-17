import asyncio
import logging
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class EventBus:
    """
    Thread-safe event bus for broadcasting task events.

    This implementation uses asyncio.Lock for thread-safe subscriber management
    and emits events concurrently to all subscribers with error isolation.

    Features:
        - Thread-safe subscribe/unsubscribe operations
        - Concurrent event emission to all subscribers
        - Error isolation (one subscriber's error doesn't affect others)
        - Async-safe list iteration

    Example:
        async def my_subscriber(event: dict):
            print(f"Received: {event}")

        event_bus.subscribe(my_subscriber)
        await event_bus.emit({'type': 'task.update', 'task': {...}})
        await event_bus.unsubscribe(my_subscriber)
    """

    def __init__(self):
        self._subscribers: list[Callable[[dict], Awaitable[None]]] = []
        self._lock = asyncio.Lock()

    def subscribe(self, fn: Callable[[dict], Awaitable[None]]):
        """
        Subscribe to events (sync method for backward compatibility).

        Note: This is synchronous but modifies shared state.
        For async contexts, consider using async_subscribe instead.

        Args:
            fn: Async function that receives event dict
        """
        self._subscribers.append(fn)

    async def async_subscribe(self, fn: Callable[[dict], Awaitable[None]]):
        """
        Subscribe to events (async-safe).

        Args:
            fn: Async function that receives event dict
        """
        async with self._lock:
            self._subscribers.append(fn)

    async def unsubscribe(self, fn: Callable[[dict], Awaitable[None]]):
        """
        Unsubscribe from events.

        Args:
            fn: The subscriber function to remove
        """
        async with self._lock:
            if fn in self._subscribers:
                self._subscribers.remove(fn)

    async def emit(self, event: dict):
        """
        Emit event to all subscribers concurrently.

        Events are delivered to all subscribers in parallel using asyncio.gather.
        If a subscriber raises an exception, it's logged but doesn't affect others.

        Args:
            event: Event dict to broadcast
        """
        # Get snapshot of subscribers under lock to avoid modification during iteration
        async with self._lock:
            subscribers = list(self._subscribers)

        # Emit to all subscribers concurrently
        if subscribers:
            tasks = [
                asyncio.create_task(self._safe_emit(fn, event))
                for fn in subscribers
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_emit(self, fn: Callable[[dict], Awaitable[None]], event: dict):
        """
        Safely emit event to a single subscriber with error handling.

        Args:
            fn: Subscriber function
            event: Event dict
        """
        try:
            await fn(event)
        except Exception as e:
            # Log error but don't crash - isolate subscriber failures
            logger.error("Error in subscriber %s: %s", fn.__name__, e, exc_info=True)


event_bus = EventBus()
