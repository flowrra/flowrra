# WebSocket Real-Time Task Updates

This guide explains how to enable real-time task updates via WebSocket in Flowrra. WebSocket support is **optional** - the frontend automatically falls back to polling (every 15 seconds) if WebSocket is unavailable.

## Overview

Flowrra's UI can receive real-time task updates through WebSocket connections, providing instant feedback when tasks change state (pending → running → success/failed). This eliminates the need for page refreshes or polling.

### Architecture

```
Task Execution → event_bus.emit() → WebSocket Subscribers → Frontend Updates (No Reload)
```

**Event Format:**
```json
{
    "type": "task.update",
    "task": {
        "task_id": "...",
        "status": "running",
        "task_name": "...",
        "started_at": "2025-01-15T10:30:00",
        ...
    }
}
```

### When to Use WebSocket

**Use WebSocket when:**
- You need real-time updates without page reloads
- Multiple users are monitoring the same dashboard
- Tasks update frequently
- You want better UX and lower bandwidth usage

**Skip WebSocket when:**
- You have a simple setup and prefer minimal dependencies
- Deployment complexity is a concern
- Polling every 15 seconds is acceptable
- You're using standard WSGI deployment (not ASGI)

---

## FastAPI (Already Configured) ✅

FastAPI has built-in WebSocket support that's **already configured** in Flowrra.

**Location:** `flowrra/src/flowrra/ui/fastapi.py`

The WebSocket endpoint at `/flowrra/ws` is automatically available when you use the FastAPI adapter. No additional configuration needed!

**Deployment:**
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
# or
hypercorn app:app --bind 0.0.0.0:8000
```

---

## Django Setup

Django requires **Django-Channels** for WebSocket support because standard Django (WSGI) doesn't handle WebSockets. Channels adds ASGI support to Django.

### Step 1: Install Dependencies

```bash
pip install channels channels-redis
```

**Why channels-redis?**
- Channels needs a channel layer for communication between processes
- Redis is the recommended backend (in-memory also available for development)

### Step 2: Update Django Settings

**In your `settings.py`:**

```python
# Add channels to installed apps
INSTALLED_APPS = [
    'channels',  # Add this
    # ... your other apps
]

# Configure ASGI application
ASGI_APPLICATION = 'your_project.asgi.application'

# Configure channel layers (required for WebSocket)
CHANNEL_LAYERS = {
    'default': {
        # Production: Use Redis
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },

        # Development: Use in-memory (simpler, but single-process only)
        # 'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
```

### Step 3: Create/Update ASGI Configuration

**Create or update `your_project/asgi.py`:**

```python
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Import Flowrra WebSocket patterns
from flowrra.ui.django_websocket import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

# IMPORTANT: Initialize Django ASGI application before importing models
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': URLRouter(websocket_urlpatterns),
})
```

**Alternative: Separate Routing File**

For cleaner separation, create `your_project/routing.py`:

```python
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from flowrra.ui.django_websocket import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': URLRouter(websocket_urlpatterns),
})
```

Then in `asgi.py`:
```python
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

# Import routing after setting Django environment
from your_project.routing import application
```

### Step 4: Deploy with ASGI Server

Django-Channels requires an ASGI server (not WSGI like gunicorn).

**Option 1: Daphne (Recommended for Django-Channels)**
```bash
pip install daphne

# Run server
daphne -b 0.0.0.0 -p 8000 your_project.asgi:application

# Production with multiple workers
daphne -b 0.0.0.0 -p 8000 --workers 4 your_project.asgi:application
```

**Option 2: Uvicorn (Faster, but less Django-specific)**
```bash
pip install uvicorn

# Run server
uvicorn your_project.asgi:application --host 0.0.0.0 --port 8000

# Production with multiple workers
uvicorn your_project.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

### Step 5: Verify WebSocket Connection

1. Start your Django app with ASGI server
2. Open the Flowrra dashboard in your browser
3. Open browser DevTools → Console
4. Look for: `"WS connected"` or `"WS disconnected → enabling polling"`

**If connected:** You'll see `WS connected` and real-time updates
**If not connected:** Frontend falls back to polling (still works, just not real-time)

### Troubleshooting Django

**Error: "No module named 'channels'"**
- Solution: `pip install channels channels-redis`

**Error: "WebSocket connection failed"**
- Check Redis is running: `redis-cli ping` (should return "PONG")
- Check ASGI_APPLICATION setting points to correct module
- Verify you're using ASGI server (daphne/uvicorn), not WSGI (gunicorn)

**Error: "ImproperlyConfigured: CHANNEL_LAYERS not configured"**
- Add CHANNEL_LAYERS to settings.py (see Step 2)

**Frontend shows polling instead of WebSocket:**
- Check browser console for WebSocket errors
- Verify endpoint is accessible: Open `ws://localhost:8000/flowrra/ws` in a WebSocket client
- Check firewall/proxy isn't blocking WebSocket connections

**Multiple workers but events not broadcasting:**
- Ensure you're using Redis channel layer (not InMemoryChannelLayer)
- Verify all workers can connect to the same Redis instance

---

## Flask/Quart Setup

Standard Flask doesn't support WebSockets natively. You need to migrate to **Quart**, which is an async-compatible reimplementation of Flask.

### Why Quart?

- **API-compatible with Flask:** Most Flask code works without changes
- **Async support:** Built on asyncio, supports WebSockets natively
- **Easy migration:** Usually just `s/flask/quart/g`

### Step 1: Install Quart

```bash
pip install quart
```

### Step 2: Migrate Flask → Quart

**Before (Flask):**
```python
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run()
```

**After (Quart):**
```python
from quart import Quart, render_template

app = Quart(__name__)  # Changed Flask → Quart

@app.route('/')
async def index():  # Added async
    return await render_template('index.html')  # Added await

if __name__ == '__main__':
    app.run()  # Quart handles this async automatically
```

### Step 3: Add Flowrra WebSocket Support

```python
from quart import Quart
from flowrra import Flowrra
from flowrra.ui.quart_websocket import setup_websocket

app = Quart(__name__)

# Create Flowrra instance
flowrra = Flowrra.from_urls()

# Setup WebSocket endpoint (automatically registers at /flowrra/ws)
setup_websocket(app)

# ... rest of your routes
```

**Manual WebSocket Registration (if you want custom path):**
```python
from flowrra.ui.quart_websocket import websocket_endpoint

@app.websocket('/custom/path/ws')
async def custom_ws():
    await websocket_endpoint()
```

### Step 4: Deploy with ASGI Server

Quart requires an ASGI server:

**Option 1: Hypercorn (Recommended for Quart)**
```bash
pip install hypercorn

# Run server
hypercorn app:app --bind 0.0.0.0:8000

# Production with multiple workers
hypercorn app:app --bind 0.0.0.0:8000 --workers 4
```

**Option 2: Uvicorn**
```bash
pip install uvicorn

# Run server
uvicorn app:app --host 0.0.0.0 --port 8000

# Production with multiple workers
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Step 5: Update Frontend WebSocket Path (if custom)

If you used a custom WebSocket path, update the frontend:

**In your template or JavaScript:**
```javascript
// Default path (no change needed)
const WS_ENDPOINT = `${protocol}://${location.host}/flowrra/ws`;

// Custom path (if you changed it)
const WS_ENDPOINT = `${protocol}://${location.host}/custom/path/ws`;
```

### Troubleshooting Quart

**Error: "No module named 'quart'"**
- Solution: `pip install quart`

**Error: "asyncio.run() cannot be called from a running event loop"**
- Quart is already running in async context, don't wrap in `asyncio.run()`

**Flask extensions not working:**
- Look for Quart-compatible versions (e.g., `flask-sqlalchemy` → `quart-sqlalchemy`)
- Many Flask extensions work directly, but async-aware ones are better

**WebSocket connection fails:**
- Ensure you're using ASGI server (hypercorn/uvicorn), not WSGI (gunicorn/waitress)
- Check browser console for connection errors
- Verify endpoint: `ws://localhost:8000/flowrra/ws`

---

## Testing WebSocket Connection

### Browser DevTools Test

1. Open Flowrra dashboard
2. Open DevTools → Console
3. Trigger a task execution
4. Watch for real-time updates in the UI (no page reload)
5. Check console logs:
   - `"WS connected"` = WebSocket working
   - `"WS disconnected → enabling polling"` = Fell back to polling

### Manual WebSocket Test

**Using `websocat` (CLI tool):**
```bash
# Install
cargo install websocat
# or
brew install websocat

# Connect to WebSocket
websocat ws://localhost:8000/flowrra/ws

# You should receive JSON events when tasks update
```

**Using Python:**
```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/flowrra/ws"
    async with websockets.connect(uri) as websocket:
        print("Connected!")
        while True:
            message = await websocket.recv()
            event = json.loads(message)
            print(f"Received: {event}")

asyncio.run(test_websocket())
```

**Using Browser Console:**
```javascript
const ws = new WebSocket('ws://localhost:8000/flowrra/ws');
ws.onopen = () => console.log('Connected!');
ws.onmessage = (e) => console.log('Received:', JSON.parse(e.data));
ws.onerror = (e) => console.error('Error:', e);
ws.onclose = () => console.log('Disconnected');
```

---

## Production Considerations

### Security

**Use WSS (WebSocket Secure) in production:**
```javascript
// Frontend automatically handles this
const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
const wsUrl = `${protocol}://${location.host}/flowrra/ws`;
```

**Nginx WebSocket proxy:**
```nginx
location /flowrra/ws {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400;  # 24 hours for long-lived connections
}
```

### Scaling

**Multiple workers:**
- Django: Use Redis channel layer (channels-redis)
- Quart: Share event_bus across workers via Redis pub/sub

**Load balancing:**
- Use sticky sessions or Redis for WebSocket state
- Ensure all workers connect to same Redis instance

### Monitoring

**Check WebSocket health:**
```python
# Count active WebSocket connections
import asyncio

async def count_subscribers():
    from flowrra.events import event_bus
    return len(event_bus._subscribers)
```

**Metrics to track:**
- Active WebSocket connections
- Event emission rate
- Subscriber errors (check logs for `[EventBus] Error in subscriber`)

---

## Comparison Table

| Feature | FastAPI | Django | Flask/Quart |
|---------|---------|--------|-------------|
| **WebSocket Support** | ✅ Built-in | ⚙️ Requires Channels | ⚙️ Requires Quart |
| **Setup Complexity** | ⭐ Simple | ⭐⭐⭐ Complex | ⭐⭐ Moderate |
| **Extra Dependencies** | None | channels, channels-redis | quart |
| **Deployment** | ASGI (uvicorn) | ASGI (daphne/uvicorn) | ASGI (hypercorn/uvicorn) |
| **Backward Compat** | N/A | Django code works | Flask → Quart migration |
| **Channel Layer** | Not needed | Redis required | Not needed |
| **Multi-worker** | ✅ Works | ✅ With Redis | ✅ Works |

---

## Summary

### Quick Start by Framework

**FastAPI:**
```bash
# Nothing to do - already works!
uvicorn app:app
```

**Django:**
```bash
pip install channels channels-redis
# Update settings.py and asgi.py (see above)
daphne your_project.asgi:application
```

**Flask → Quart:**
```bash
pip install quart
# Change: Flask → Quart, add async/await
# Add: setup_websocket(app)
hypercorn app:app
```

### Without WebSocket

If you **don't** want to setup WebSocket, that's fine! The frontend automatically falls back to:
- Polling every 15 seconds
- Still shows task updates (just not instant)
- No code changes needed

### Getting Help

**WebSocket not connecting?**
1. Check browser console for errors
2. Verify ASGI server (not WSGI)
3. Test with `websocat` or browser console
4. Check Redis connection (Django only)

**Still polling instead of WebSocket?**
- This is normal if WebSocket setup is skipped
- Check console: `"WS disconnected → enabling polling"`
- Frontend works fine either way!

---

## Additional Resources

- [Django Channels Documentation](https://channels.readthedocs.io/)
- [Quart Documentation](https://quart.palletsprojects.com/)
- [WebSocket Protocol (RFC 6455)](https://tools.ietf.org/html/rfc6455)
- [Flowrra Event Bus Source](../flowrra/src/flowrra/events.py)
- [Flowrra Django WebSocket Consumer](../flowrra/src/flowrra/ui/django_websocket.py)
- [Flowrra Quart WebSocket Support](../flowrra/src/flowrra/ui/quart_websocket.py)
