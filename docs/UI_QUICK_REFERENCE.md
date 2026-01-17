# Flowrra UI Quick Reference

Quick reference guide for integrating Flowrra Web UI into your application.

## Installation

```bash
# Choose your framework
pip install flowrra[ui-fastapi]    # FastAPI
pip install flowrra[ui-flask]      # Flask/Quart
pip install flowrra[ui-django]     # Django
pip install flowrra[ui]            # All adapters
```

## FastAPI Integration

```python
from fastapi import FastAPI
from flowrra import Flowrra
from flowrra.ui.fastapi import create_router

app = FastAPI()
flowrra = Flowrra.from_urls()

@flowrra.task()
async def my_task(x: int):
    return x * 2

# Mount UI
app.include_router(create_router(flowrra), prefix="/flowrra")

@app.on_event("startup")
async def startup():
    await flowrra.start()

@app.on_event("shutdown")
async def shutdown():
    await flowrra.stop()

# Run: uvicorn main:app
# Visit: http://localhost:8000/flowrra/
```

## Flask/Quart Integration

```python
from quart import Quart
from flowrra import Flowrra
from flowrra.ui.flask import create_blueprint

app = Quart(__name__)
flowrra = Flowrra.from_urls()

@flowrra.task()
async def my_task(x: int):
    return x * 2

# Mount UI
app.register_blueprint(create_blueprint(flowrra), url_prefix="/flowrra")

@app.before_serving
async def startup():
    await flowrra.start()

@app.after_serving
async def shutdown():
    await flowrra.stop()

# Run: quart run
# Visit: http://localhost:8000/flowrra/
```

## Django Integration

```python
# urls.py
from django.urls import path, include
from flowrra import Flowrra
from flowrra.ui.django import get_urls

flowrra = Flowrra.from_urls()

@flowrra.task()
async def my_task(x: int):
    return x * 2

urlpatterns = [
    path('flowrra/', include(get_urls(flowrra))),
]

# apps.py
from django.apps import AppConfig
import asyncio

class MyAppConfig(AppConfig):
    def ready(self):
        asyncio.create_task(flowrra.start())

# Run: python manage.py runserver
# Visit: http://localhost:8000/flowrra/
```

## API Endpoints

### System
- `GET /api/stats` - System statistics
- `GET /api/health` - Health check

### Tasks
- `GET /api/tasks` - List all tasks
- `GET /api/tasks/{name}` - Get task details

### Schedules
- `GET /api/schedules` - List schedules
- `POST /api/schedules/cron` - Create schedule
- `PUT /api/schedules/{id}/enable` - Enable schedule
- `PUT /api/schedules/{id}/disable` - Disable schedule
- `DELETE /api/schedules/{id}` - Delete schedule

## HTML Pages

- `/` - Dashboard (system overview)
- `/tasks` - Tasks page (with filtering)
- `/schedules` - Schedules page (management)

## Add Authentication

### FastAPI
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_auth(creds: HTTPBasicCredentials = Depends(security)):
    if creds.username != "admin" or creds.password != "secret":
        raise HTTPException(401)
    return creds

app.include_router(
    create_router(flowrra),
    prefix="/flowrra",
    dependencies=[Depends(verify_auth)]
)
```

### Flask/Quart
```python
from functools import wraps

def require_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != 'secret':
            abort(401)
        return await f(*args, **kwargs)
    return decorated

blueprint = create_blueprint(flowrra)

@blueprint.before_request
@require_auth
async def check_auth():
    pass
```

### Django
```python
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('flowrra/', include(get_urls(flowrra))),
]

# Apply login_required to all views
from flowrra.ui.django import DjangoAdapter
adapter = DjangoAdapter(flowrra)
patterns = adapter.get_routes()

authenticated = [
    path(p.pattern._route, login_required(p.callback), name=p.name)
    for p in patterns
]
```

## Custom Styling

```html
<!-- Add custom CSS -->
<style>
  .flowrra-dashboard { background: #f5f5f5; }
  .task-card { border-radius: 8px; }
</style>
```

## Production Setup

### FastAPI with Uvicorn
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Quart with Hypercorn
```bash
hypercorn main:app --bind 0.0.0.0:8000 --workers 4
```

### Django with Gunicorn
```bash
gunicorn myproject.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## Environment Variables

```bash
# Database URLs
export FLOWRRA_BACKEND="redis://localhost:6379/0"
export FLOWRRA_SCHEDULER_BACKEND="postgresql://localhost/flowrra"

# Configuration
export FLOWRRA_NUM_WORKERS="4"
export FLOWRRA_CPU_WORKERS="2"
```

## Troubleshooting

### Static files not loading
- FastAPI: Ensure StaticFiles middleware is mounted
- Django: Run `python manage.py collectstatic`
- Check browser console for 404 errors

### Templates not found
- Verify template directory exists
- Check framework-specific template configuration
- Ensure templates are in correct directory

### CORS errors
- Add CORS middleware to your app
- Configure allowed origins
- Enable credentials if needed

### Port already in use
```bash
# Use different port
uvicorn main:app --port 8001
quart run --port 8001
python manage.py runserver 8001
```

## Examples

Full working examples in `examples/` directory:
- `fastapi_ui_example.py`
- `quart_ui_example.py`
- `django_ui_example.py`

Run with:
```bash
python examples/fastapi_ui_example.py
python examples/quart_ui_example.py
python examples/django_ui_example.py
```

## Full Documentation

See [UI.md](../UI.md) for comprehensive documentation including:
- Detailed integration guides
- Complete API reference
- Customization options
- Production deployment
- Security best practices

## Support

- **Documentation**: [UI.md](../UI.md)
- **Main README**: [README.md](../README.md)
- **Scheduler**: [SCHEDULER.md](../SCHEDULER.md)
