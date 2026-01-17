"""
Quart WebSocket Support for Flowrra

Provides real-time task updates via WebSocket for Flask/Quart applications.

Note: This requires Quart, which is an async-compatible reimplementation of Flask.
Standard Flask does not support WebSockets natively.

Installation:
    pip install quart

Migration from Flask to Quart:
    Quart is API-compatible with Flask, making migration straightforward:
    - Replace 'from flask import Flask' with 'from quart import Quart'
    - Replace 'flask run' with 'quart run' or use hypercorn/uvicorn
    - Most Flask extensions work with Quart equivalents

Usage Example:
    from quart import Quart
    from flowrra import Flowrra
    from flowrra.ui.quart_websocket import setup_websocket

    app = Quart(__name__)
    flowrra = Flowrra.from_urls()

    # Setup WebSocket endpoint
    setup_websocket(app)

    # Run with ASGI server
    # quart run
    # or: hypercorn app:app
    # or: uvicorn app:app

Without Quart/WebSocket, the frontend falls back to polling every 15 seconds.
"""

import asyncio
import json
import logging
from typing import Optional

try:
    from quart import websocket, Quart
    QUART_AVAILABLE = True
except ImportError:
    QUART_AVAILABLE = False
    websocket = None
    Quart = None

from flowrra.events import event_bus

logger = logging.getLogger(__name__)


async def websocket_endpoint():
    """
    Quart WebSocket endpoint for Flowrra real-time task updates.

    This function should be registered as a WebSocket route in your Quart app.

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

    Raises:
        ImportError: If Quart is not installed
    """
    if not QUART_AVAILABLE:
        raise ImportError(
            "Quart is required for WebSocket support. "
            "Install it with: pip install quart"
        )

    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def subscriber(event: dict):
        await queue.put(event)

    event_bus.subscribe(subscriber)

    # Create task to forward events from queue to WebSocket
    async def forward_events():
        try:
            while True:
                event = await queue.get()
                await websocket.send(json.dumps(event))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error forwarding event: %s", e, exc_info=True)

    forward_task = asyncio.create_task(forward_events())

    logger.info("WebSocket connected")

    try:
        while True:
            try:
                await websocket.receive()
            except Exception:
                break

    finally:
        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass

        if subscriber in event_bus._subscribers:
            event_bus._subscribers.remove(subscriber)

        logger.info("WebSocket disconnected")


def setup_websocket(app: 'Quart', path: str = '/flowrra/ws'):
    """
    Setup WebSocket endpoint in a Quart application.

    This is a convenience function to register the WebSocket route.

    Args:
        app: Quart application instance
        path: WebSocket endpoint path (default: '/flowrra/ws')

    Example:
        from quart import Quart
        from flowrra.ui.quart_websocket import setup_websocket

        app = Quart(__name__)
        setup_websocket(app)

    Raises:
        ImportError: If Quart is not installed
    """
    if not QUART_AVAILABLE:
        raise ImportError(
            "Quart is required for WebSocket support. "
            "Install it with: pip install quart"
        )

    @app.websocket(path)
    async def flowrra_ws():
        await websocket_endpoint()

    logger.info("WebSocket endpoint registered at %s", path)


__all__ = ['websocket_endpoint', 'setup_websocket', 'QUART_AVAILABLE']
