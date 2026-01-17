# Flowrra Web UI

Flowrra provides built-in web interfaces that can be easily integrated into your existing web applications. Monitor tasks, view schedules, check system health, and manage your task queue through a beautiful, responsive UI.

## Overview

The Flowrra UI system follows the **Adapter Pattern**, providing native integrations for popular Python web frameworks:

- **FastAPI** - Modern, fast, async-first framework
- **Flask/Quart** - Traditional and async-native Flask
- **Django** - Full-featured web framework

All adapters share the same:
- HTML pages (Dashboard, Tasks, Schedules)
- JSON API endpoints
- Static assets (CSS, JavaScript)
- Feature set

Choose the adapter that matches your existing web framework.

## Features

### 📊 Dashboard
- Real-time system status
- Executor statistics (IO and CPU)
- Recent task history
- Quick statistics overview

### 📋 Tasks Page
- View all registered tasks
- Filter by status (pending, running, success, failed)
- Task execution history
- Retry configuration details
- Error messages and stack traces

### 📅 Schedules Page
- Manage cron-based schedules
- View interval and one-time schedules
- Enable/disable schedules
- See next run times
- Schedule execution history

### 🔧 JSON API
- RESTful API for all operations
- Health check endpoint
- Task submission endpoints
- Schedule management endpoints
- Statistics and metrics

## Quick Start

Choose your framework and follow the integration guide:

### FastAPI

```python
from fastapi import FastAPI
from flowrra import Flowrra
from flowrra.ui.fastapi import create_router

app = FastAPI()
flowrra = Flowrra.from_urls()

# Define tasks
@flowrra.task()
async def send_email(to: str, subject: str):
    print(f"Sending email to {to}: {subject}")
    return {"sent": True}

# Mount Flowrra UI
app.include_router(
    create_router(flowrra),
    prefix="/flowrra",
    tags=["flowrra"]
)

# Lifecycle management
@app.on_event("startup")
async def startup():
    await flowrra.start()

@app.on_event("shutdown")
async def shutdown():
    await flowrra.stop()

# Run with: uvicorn main:app --reload
# Visit: http://localhost:8000/flowrra/
```

### Flask/Quart

```python
from quart import Quart
from flowrra import Flowrra
from flowrra.ui.flask import create_blueprint

app = Quart(__name__)
flowrra = Flowrra.from_urls()

# Define tasks
@flowrra.task()
async def send_email(to: str, subject: str):
    print(f"Sending email to {to}: {subject}")
    return {"sent": True}

# Mount Flowrra UI
app.register_blueprint(
    create_blueprint(flowrra),
    url_prefix="/flowrra"
)

# Lifecycle management
@app.before_serving
async def startup():
    await flowrra.start()

@app.after_serving
async def shutdown():
    await flowrra.stop()

# Run with: quart run
# Visit: http://localhost:8000/flowrra/
```

### Django

```python
# In your Django project's urls.py
from django.urls import path, include
from flowrra import Flowrra
from flowrra.ui.django import get_urls

# Create Flowrra instance (typically in settings or AppConfig)
flowrra = Flowrra.from_urls()

# Define tasks
@flowrra.task()
async def send_email(to: str, subject: str):
    print(f"Sending email to {to}: {subject}")
    return {"sent": True}

urlpatterns = [
    # ... your other URL patterns
    path('flowrra/', include(get_urls(flowrra))),
]

# In your Django app's apps.py (for lifecycle management)
from django.apps import AppConfig
import asyncio

class YourAppConfig(AppConfig):
    def ready(self):
        # Start Flowrra when Django starts
        asyncio.create_task(flowrra.start())
```

## Installation

Install Flowrra with your preferred web framework:

```bash
# FastAPI
pip install flowrra[ui-fastapi]

# Flask/Quart
pip install flowrra[ui-flask]

# Django
pip install flowrra[ui-django]

# All UI adapters
pip install flowrra[ui]
```

## Detailed Integration Guides

### FastAPI Integration

**Installation:**
```bash
pip install flowrra[ui-fastapi]
```

**Basic Setup:**
```python
from fastapi import FastAPI
from flowrra import Flowrra, Config, ExecutorConfig
from flowrra.ui.fastapi import FastAPIAdapter, create_router

# Configure Flowrra
config = Config(executor=ExecutorConfig(num_workers=4))
flowrra = Flowrra(config=config)

# Create FastAPI app
app = FastAPI(title="My App with Flowrra")

# Mount Flowrra UI
flowrra_router = create_router(flowrra)
app.include_router(
    flowrra_router,
    prefix="/flowrra",
    tags=["flowrra", "tasks"]
)
```

**Advanced: Custom Adapter:**
```python
from flowrra.ui.fastapi import FastAPIAdapter

# Create adapter with custom configuration
adapter = FastAPIAdapter(flowrra)

# Get router
router = adapter.get_routes()

# Add custom middleware or modify routes
@router.middleware("http")
async def custom_middleware(request, call_next):
    # Add custom logic
    response = await call_next(request)
    return response

# Mount with custom settings
app.include_router(router, prefix="/admin/tasks")
```

**Static Files:**
FastAPI automatically serves static files from the adapter's static directory. CSS and JavaScript are available at `/flowrra/static/`.

**OpenAPI Integration:**
The Flowrra UI endpoints are automatically included in your FastAPI OpenAPI schema. Access interactive docs at `/docs` or `/redoc`.

---

### Flask/Quart Integration

**Installation:**
```bash
pip install flowrra[ui-flask]
```

**Quart (Recommended - Async Support):**
```python
from quart import Quart
from flowrra import Flowrra, Config, ExecutorConfig
from flowrra.ui.flask import FlaskAdapter, create_blueprint

# Configure Flowrra
config = Config(executor=ExecutorConfig(num_workers=4))
flowrra = Flowrra(config=config)

# Create Quart app
app = Quart(__name__)

# Mount Flowrra UI
flowrra_blueprint = create_blueprint(flowrra)
app.register_blueprint(
    flowrra_blueprint,
    url_prefix="/flowrra"
)

# Lifecycle management
@app.before_serving
async def startup():
    await flowrra.start()

@app.after_serving
async def shutdown():
    await flowrra.stop()
```

**Traditional Flask:**
```python
from flask import Flask
from flowrra import Flowrra
from flowrra.ui.flask import create_blueprint

app = Flask(__name__)
flowrra = Flowrra.from_urls()

# Mount Flowrra UI
app.register_blueprint(
    create_blueprint(flowrra),
    url_prefix="/flowrra"
)

# Note: Flask async support is limited
# Use Quart for better async performance
```

**Advanced: Custom Blueprint:**
```python
from flowrra.ui.flask import FlaskAdapter

# Create adapter
adapter = FlaskAdapter(flowrra)

# Get blueprint
blueprint = adapter.get_routes()

# Customize blueprint
@blueprint.before_request
def before_request():
    # Add authentication, logging, etc.
    pass

# Register with custom settings
app.register_blueprint(blueprint, url_prefix="/admin/flowrra")
```

**Static Files:**
The blueprint automatically configures static file serving. Access at `/flowrra/static/`.

**Template Customization:**
Quart uses Jinja2 templates. You can override templates by placing custom versions in your app's template directory.

---

### Django Integration

**Installation:**
```bash
pip install flowrra[ui-django]
```

**URL Configuration:**
```python
# urls.py
from django.urls import path, include
from flowrra import Flowrra
from flowrra.ui.django import get_urls, DjangoAdapter

# Create Flowrra instance
flowrra = Flowrra.from_urls()

urlpatterns = [
    path('admin/', admin.site.urls),
    # ... other patterns
    path('flowrra/', include(get_urls(flowrra))),
]
```

**Advanced Setup with AppConfig:**
```python
# apps.py
from django.apps import AppConfig
import asyncio

class MyAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        """Initialize Flowrra when Django starts."""
        from flowrra import Flowrra, Config, ExecutorConfig

        # Create Flowrra instance
        config = Config(executor=ExecutorConfig(num_workers=4))
        flowrra = Flowrra(config=config)

        # Define tasks
        @flowrra.task()
        async def send_notification(user_id: int, message: str):
            # Task implementation
            pass

        # Start Flowrra
        # Note: This runs synchronously in Django's startup
        import threading

        def start_flowrra():
            asyncio.run(flowrra.start())

        thread = threading.Thread(target=start_flowrra, daemon=True)
        thread.start()

        # Store globally for access in views
        import sys
        sys.modules['myapp'].flowrra = flowrra
```

**Custom Adapter:**
```python
from flowrra.ui.django import DjangoAdapter

# Create adapter
adapter = DjangoAdapter(flowrra)

# Get URL patterns
urlpatterns = adapter.get_routes()

# Add custom middleware or authentication
from django.contrib.auth.decorators import login_required

# Wrap views with authentication
authenticated_patterns = [
    path('', login_required(pattern.callback), name=pattern.name)
    for pattern in urlpatterns
]
```

**Static Files:**
Django serves static files according to your `STATIC_URL` and `STATIC_ROOT` settings. The adapter's static files are automatically included.

**Template Customization:**
Django templates are in `flowrra/` subdirectory. Override by creating `templates/flowrra/` in your project.

---

## API Endpoints Reference

All adapters provide the same JSON API endpoints:

### System Information

#### `GET /api/stats`
Get comprehensive system statistics.

**Response:**
```json
{
  "app": {
    "running": true,
    "uptime": 3600.5
  },
  "executors": {
    "io": {
      "type": "IOExecutor",
      "workers": 4,
      "active_tasks": 2,
      "pending_tasks": 5
    },
    "cpu": {
      "type": "CPUExecutor",
      "workers": 2,
      "active_tasks": 0,
      "pending_tasks": 0
    }
  },
  "tasks": {
    "total": 10,
    "pending": 5,
    "running": 2,
    "success": 2,
    "failed": 1
  }
}
```

#### `GET /api/health`
Health check endpoint for monitoring.

**Response:**
```json
{
  "healthy": true,
  "timestamp": "2024-01-07T19:30:00.000000",
  "components": {
    "app": "healthy",
    "io_executor": "healthy",
    "cpu_executor": "healthy",
    "scheduler": "healthy"
  }
}
```

### Task Management

#### `GET /api/tasks`
List all registered tasks.

**Response:**
```json
[
  {
    "name": "send_email",
    "cpu_bound": false,
    "max_retries": 3,
    "retry_delay": 5.0,
    "priority": 0,
    "description": "Send email to user"
  },
  {
    "name": "process_image",
    "cpu_bound": true,
    "max_retries": 1,
    "retry_delay": 10.0,
    "priority": 5,
    "description": "Process image file"
  }
]
```

#### `GET /api/tasks/{task_name}`
Get detailed information about a specific task.

**Response:**
```json
{
  "name": "send_email",
  "cpu_bound": false,
  "max_retries": 3,
  "retry_delay": 5.0,
  "priority": 0,
  "description": "Send email to user",
  "recent_executions": [
    {
      "id": "task-uuid-123",
      "status": "success",
      "started_at": "2024-01-07T19:25:00",
      "completed_at": "2024-01-07T19:25:02",
      "duration": 2.1
    }
  ]
}
```

**Error Response (404):**
```json
{
  "detail": "Task not found"
}
```

### Schedule Management

#### `GET /api/schedules`
List all schedules.

**Query Parameters:**
- `enabled_only` (boolean): Only return enabled schedules

**Response:**
```json
[
  {
    "id": "schedule-uuid-123",
    "task_name": "send_email",
    "schedule_type": "cron",
    "schedule": "0 9 * * *",
    "enabled": true,
    "next_run_at": "2024-01-08T09:00:00",
    "last_run_at": "2024-01-07T09:00:00",
    "description": "Daily morning email"
  },
  {
    "id": "schedule-uuid-456",
    "task_name": "cleanup_cache",
    "schedule_type": "interval",
    "schedule": "3600",
    "enabled": true,
    "next_run_at": "2024-01-07T20:30:00",
    "last_run_at": "2024-01-07T19:30:00",
    "description": "Hourly cache cleanup"
  }
]
```

#### `GET /api/schedules/{schedule_id}`
Get detailed information about a specific schedule.

**Response:**
```json
{
  "id": "schedule-uuid-123",
  "task_name": "send_email",
  "schedule_type": "cron",
  "schedule": "0 9 * * *",
  "args": ["user@example.com"],
  "kwargs": {"subject": "Daily Report"},
  "enabled": true,
  "priority": 0,
  "next_run_at": "2024-01-08T09:00:00",
  "last_run_at": "2024-01-07T09:00:00",
  "created_at": "2024-01-01T00:00:00",
  "description": "Daily morning email"
}
```

#### `POST /api/schedules/cron`
Create a new cron-based schedule.

**Request Body:**
```json
{
  "task_name": "send_email",
  "cron": "0 9 * * *",
  "args": ["user@example.com"],
  "kwargs": {"subject": "Daily Report"},
  "enabled": true,
  "priority": 0,
  "description": "Daily morning email"
}
```

**Response (201):**
```json
{
  "id": "schedule-uuid-789",
  "task_name": "send_email",
  "schedule_type": "cron",
  "schedule": "0 9 * * *",
  "enabled": true,
  "next_run_at": "2024-01-08T09:00:00",
  "created_at": "2024-01-07T19:30:00"
}
```

**Error Response (400):**
```json
{
  "error": "Invalid cron expression"
}
```

#### `PUT /api/schedules/{schedule_id}/enable`
Enable a schedule.

**Response:**
```json
{
  "id": "schedule-uuid-123",
  "enabled": true,
  "message": "Schedule enabled successfully"
}
```

#### `PUT /api/schedules/{schedule_id}/disable`
Disable a schedule.

**Response:**
```json
{
  "id": "schedule-uuid-123",
  "enabled": false,
  "message": "Schedule disabled successfully"
}
```

#### `DELETE /api/schedules/{schedule_id}`
Delete a schedule permanently.

**Response:**
```json
{
  "id": "schedule-uuid-123",
  "message": "Schedule deleted successfully"
}
```

---

## HTML Pages

### Dashboard (`/`)
The main dashboard provides an overview of your Flowrra system:

- **System Status**: Running state, uptime
- **Executor Statistics**: Worker counts, active tasks, pending queues
- **Recent Tasks**: Last 10 task executions with status
- **Quick Stats**: Total tasks, success rate, failure count

### Tasks Page (`/tasks`)
View and manage all registered tasks:

- **Task List**: All registered tasks with configuration
- **Filter by Status**: pending, running, success, failed
- **Task Details**: Click a task to see full details
- **Execution History**: Recent runs with timing and results
- **Error Details**: Stack traces for failed tasks

**URL Parameters:**
- `?status=pending` - Filter by status
- `?status=failed` - Show only failed tasks

### Schedules Page (`/schedules`)
Manage scheduled tasks:

- **Schedule List**: All schedules with next run times
- **Enable/Disable**: Toggle schedules on/off
- **Create Schedule**: Add new cron or interval schedules
- **Edit Schedule**: Modify existing schedules
- **Delete Schedule**: Remove schedules

**URL Parameters:**
- `?enabled_only=true` - Show only enabled schedules

---

## Customization

### Styling

All adapters use the same CSS file located at `/static/style.css`. You can customize the appearance by:

**Option 1: Override CSS**
```html
<!-- Add custom styles in your app -->
<style>
  .flowrra-dashboard { background: #f5f5f5; }
  .task-card { border-radius: 8px; }
</style>
```

**Option 2: Custom Stylesheet**
Create your own stylesheet and include it after Flowrra's CSS to override styles.

**CSS Classes:**
- `.flowrra-dashboard` - Dashboard container
- `.task-card` - Individual task cards
- `.schedule-item` - Schedule list items
- `.status-badge` - Status indicator badges
- `.executor-stats` - Executor statistics panels

### Templates

Each adapter uses templates from `flowrra/ui/templates/`:

**FastAPI/Quart (Jinja2):**
Override by creating templates in your app's template directory with the same names:
- `dashboard.html`
- `tasks.html`
- `schedules.html`
- `base.html`

**Django:**
Override by creating templates in `templates/flowrra/`:
- `templates/flowrra/dashboard.html`
- `templates/flowrra/tasks.html`
- `templates/flowrra/schedules.html`
- `templates/flowrra/base.html`

**Template Variables:**

All templates receive these context variables:
- `app` - Flowrra app instance
- `stats` - System statistics
- `tasks` - List of tasks
- `schedules` - List of schedules
- `format_datetime` - Function to format timestamps
- `format_duration` - Function to format durations
- `get_status_color` - Function to get badge color for status

### Authentication

Add authentication to protect Flowrra UI:

**FastAPI:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != "admin" or credentials.password != "secret":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    return credentials

# Add authentication to router
flowrra_router = create_router(flowrra)
app.include_router(
    flowrra_router,
    prefix="/flowrra",
    dependencies=[Depends(verify_credentials)]
)
```

**Flask/Quart:**
```python
from quart import request, abort
from functools import wraps

def require_auth(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != 'admin' or auth.password != 'secret':
            abort(401)
        return await f(*args, **kwargs)
    return decorated_function

# Apply to blueprint
blueprint = create_blueprint(flowrra)

@blueprint.before_request
@require_auth
async def before_request():
    pass

app.register_blueprint(blueprint, url_prefix="/flowrra")
```

**Django:**
```python
from django.contrib.auth.decorators import login_required
from flowrra.ui.django import DjangoAdapter

adapter = DjangoAdapter(flowrra)
urlpatterns = adapter.get_routes()

# Wrap all views with authentication
authenticated_patterns = [
    path(
        pattern.pattern._route,
        login_required(pattern.callback),
        name=pattern.name
    )
    for pattern in urlpatterns
]
```

### CORS Configuration

If your UI is accessed from a different origin:

**FastAPI:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Flask/Quart:**
```python
from quart_cors import cors

app = cors(app, allow_origin="https://yourdomain.com")
```

**Django:**
```python
# Install django-cors-headers
# pip install django-cors-headers

# settings.py
INSTALLED_APPS = [
    'corsheaders',
    # ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ...
]

CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
]
```

---

## Production Deployment

### Security Checklist

- [ ] Enable authentication/authorization
- [ ] Use HTTPS in production
- [ ] Configure CORS properly
- [ ] Set secure session cookies
- [ ] Rate limit API endpoints
- [ ] Validate all input data
- [ ] Use environment variables for secrets
- [ ] Enable CSRF protection (Django)
- [ ] Configure CSP headers
- [ ] Monitor access logs

### Performance Tips

1. **Use a production server:**
   - FastAPI: Use `uvicorn` with multiple workers
   - Flask/Quart: Use `gunicorn` or `hypercorn`
   - Django: Use `gunicorn` or `uwsgi`

2. **Enable caching:**
   ```python
   # Cache dashboard data
   from functools import lru_cache

   @lru_cache(maxsize=1)
   def get_dashboard_data_cached():
       return adapter.get_dashboard_data()
   ```

3. **Optimize database queries:**
   - Use connection pooling
   - Add indexes on frequently queried fields
   - Use read replicas for scaling

4. **Static file serving:**
   - Use a CDN or reverse proxy (nginx, Apache)
   - Enable gzip compression
   - Set proper cache headers

### Example Production Setup (FastAPI + Nginx)

**FastAPI app with Uvicorn:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Nginx configuration:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /flowrra/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /flowrra/static/ {
        alias /path/to/flowrra/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Troubleshooting

### Common Issues

**1. Static files not loading**

FastAPI:
```python
# Ensure you mount StaticFiles
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")
```

Django:
```python
# Ensure STATIC_URL is configured
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Run collectstatic
python manage.py collectstatic
```

**2. Templates not found**

Check that template directory exists and is configured:
```python
# FastAPI
templates = Jinja2Templates(directory="templates")

# Flask/Quart
app = Quart(__name__, template_folder="templates")

# Django
TEMPLATES = [{
    'DIRS': [BASE_DIR / 'templates'],
    # ...
}]
```

**3. CORS errors**

Enable CORS middleware (see CORS Configuration section above).

**4. Async errors in Django**

Django views are sync by default. Use the provided `async_to_sync_view` decorator or run tasks in a separate thread.

**5. Port already in use**

Change the port:
```bash
# FastAPI
uvicorn main:app --port 8001

# Flask/Quart
quart run --port 8001

# Django
python manage.py runserver 8001
```

---

## Examples

Complete example applications are available in the `examples/` directory:

- `examples/fastapi_ui_example.py` - FastAPI integration
- `examples/quart_ui_example.py` - Quart integration
- `examples/django_ui_example.py` - Django integration

Run any example:
```bash
# FastAPI
python examples/fastapi_ui_example.py

# Quart
python examples/quart_ui_example.py

# Django
python examples/django_ui_example.py
```

---

## API Client Examples

### Python Client

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Get system stats
        response = await client.get("http://localhost:8000/flowrra/api/stats")
        stats = response.json()
        print(f"Active tasks: {stats['tasks']['running']}")

        # Create a schedule
        schedule = {
            "task_name": "send_email",
            "cron": "0 9 * * *",
            "args": ["user@example.com"],
            "kwargs": {"subject": "Daily Report"},
            "enabled": True
        }
        response = await client.post(
            "http://localhost:8000/flowrra/api/schedules/cron",
            json=schedule
        )
        print(f"Schedule created: {response.json()['id']}")

asyncio.run(main())
```

### JavaScript/TypeScript Client

```typescript
// Get system stats
const stats = await fetch('http://localhost:8000/flowrra/api/stats')
  .then(res => res.json());
console.log(`Active tasks: ${stats.tasks.running}`);

// Create a schedule
const schedule = {
  task_name: 'send_email',
  cron: '0 9 * * *',
  args: ['user@example.com'],
  kwargs: { subject: 'Daily Report' },
  enabled: true
};

const response = await fetch('http://localhost:8000/flowrra/api/schedules/cron', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(schedule)
});

const result = await response.json();
console.log(`Schedule created: ${result.id}`);
```

### cURL Examples

```bash
# Get system stats
curl http://localhost:8000/flowrra/api/stats

# Get health status
curl http://localhost:8000/flowrra/api/health

# List all tasks
curl http://localhost:8000/flowrra/api/tasks

# Get specific task
curl http://localhost:8000/flowrra/api/tasks/send_email

# List schedules
curl http://localhost:8000/flowrra/api/schedules

# Create a schedule
curl -X POST http://localhost:8000/flowrra/api/schedules/cron \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "send_email",
    "cron": "0 9 * * *",
    "args": ["user@example.com"],
    "kwargs": {"subject": "Daily Report"},
    "enabled": true
  }'

# Enable a schedule
curl -X PUT http://localhost:8000/flowrra/api/schedules/{schedule_id}/enable

# Disable a schedule
curl -X PUT http://localhost:8000/flowrra/api/schedules/{schedule_id}/disable

# Delete a schedule
curl -X DELETE http://localhost:8000/flowrra/api/schedules/{schedule_id}
```

---

## Next Steps

- Explore the [Scheduler Documentation](SCHEDULER.md)
- Learn about [Task Configuration](README.md#tasks)
- Set up [Production Deployment](#production-deployment)
- Check out the [Examples](#examples)

## Support

- **Documentation**: https://github.com/yourusername/flowrra
- **Issues**: https://github.com/yourusername/flowrra/issues
- **Discussions**: https://github.com/yourusername/flowrra/discussions
