"""
Django WebSocket Consumer for Flowrra

Provides real-time task updates via WebSocket using Django-Channels.

This module is optional and requires Django-Channels to be installed.
Users who don't want WebSocket support can rely on the frontend's
polling fallback mechanism (15-second intervals).

Usage Example:
    1. Install Django-Channels:
        pip install channels channels-redis

    2. Configure ASGI in your Django settings.py:
        ASGI_APPLICATION = 'your_project.asgi.application'
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels_redis.core.RedisChannelLayer',
                'CONFIG': {
                    'hosts': [('127.0.0.1', 6379)],
                },
            },
        }

    3. Create/update your routing.py:
        from channels.routing import ProtocolTypeRouter, URLRouter
        from django.core.asgi import get_asgi_application
        from flowrra.ui.django_websocket import websocket_urlpatterns

        application = ProtocolTypeRouter({
            'http': get_asgi_application(),
            'websocket': URLRouter(websocket_urlpatterns),
        })

    4. Deploy with an ASGI server:
        daphne -b 0.0.0.0 -p 8000 your_project.asgi:application
        # or
        uvicorn your_project.asgi:application --host 0.0.0.0 --port 8000

Without WebSocket setup, the frontend automatically falls back to polling.
"""

import asyncio
import json
import logging
from typing import Optional

try:
    from channels.generic.websocket import AsyncWebsocketConsumer
    from django.urls import path
    CHANNELS_AVAILABLE = True
except ImportError:
    CHANNELS_AVAILABLE = False
    # Provide a dummy base class when channels is not installed
    class AsyncWebsocketConsumer:
        pass


from flowrra.events import event_bus

logger = logging.getLogger(__name__)


class FlowrraConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time Flowrra task updates.

    This consumer subscribes to the global event_bus and forwards
    task update events to connected WebSocket clients.

    Architecture:
        - Uses an asyncio.Queue to decouple event_bus from WebSocket send
        - Subscriber function puts events into the queue
        - Separate task reads from queue and sends to WebSocket
        - Prevents blocking the event_bus if WebSocket is slow

    Events Format:
        {
            'type': 'task.update',
            'task': {
                'task_id': str,
                'status': 'pending|running|success|failed|retrying',
                'task_name': str,
                'result': Any,
                'error': str | None,
                'submitted_at': ISO datetime,
                'started_at': ISO datetime,
                'finished_at': ISO datetime,
                'retries': int,
                # ... additional task fields
            }
        }
    """

    def __init__(self, *args, **kwargs):
        if not CHANNELS_AVAILABLE:
            raise ImportError(
                "Django-Channels is required for WebSocket support. "
                "Install it with: pip install channels"
            )
        super().__init__(*args, **kwargs)
        self.queue: Optional[asyncio.Queue] = None
        self.subscriber: Optional[callable] = None
        self.forward_task: Optional[asyncio.Task] = None

    async def connect(self):
        """
        Handle WebSocket connection.

        Creates a queue for this connection, subscribes to the event_bus,
        and starts a task to forward events from queue to WebSocket.
        """
        await self.accept()

        self.queue = asyncio.Queue()

        async def subscriber(event: dict):
            if self.queue:
                await self.queue.put(event)

        self.subscriber = subscriber
        event_bus.subscribe(subscriber)

        self.forward_task = asyncio.create_task(self._forward_events())

        logger.info("WebSocket connected: %s", self.channel_name)

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        Stops the forwarding task, unsubscribes from event_bus,
        and cleans up resources.
        """
        if self.forward_task and not self.forward_task.done():
            self.forward_task.cancel()
            try:
                await self.forward_task
            except asyncio.CancelledError:
                pass

        if self.subscriber and self.subscriber in event_bus._subscribers:
            event_bus._subscribers.remove(self.subscriber)

        self.queue = None
        self.subscriber = None
        self.forward_task = None

        logger.info("WebSocket disconnected: %s (code: %s)", self.channel_name, close_code)

    async def _forward_events(self):
        """
        Forward events from queue to WebSocket.

        This runs in a separate task to decouple event_bus emission
        from WebSocket send operations.
        """
        try:
            while True:
                event = await self.queue.get()
                await self.send(text_data=json.dumps(event))

        except asyncio.CancelledError:
            # Normal cancellation during disconnect
            pass
        except Exception as e:
            logger.error("Error forwarding event: %s", e, exc_info=True)


if CHANNELS_AVAILABLE:
    websocket_urlpatterns = [
        path('flowrra/ws', FlowrraConsumer.as_asgi()),
    ]
else:
    # Provide empty list when channels is not available
    websocket_urlpatterns = []


__all__ = ['FlowrraConsumer', 'websocket_urlpatterns', 'CHANNELS_AVAILABLE']
