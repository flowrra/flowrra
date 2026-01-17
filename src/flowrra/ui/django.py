"""Django adapter for Flowrra UI.

This module provides Django URLs and views that can be included in existing
Django applications to add Flowrra's management interface.

Installation:
    pip install flowrra[ui-django]

Example:
    # In your Django project's urls.py
    from django.urls import path, include
    from flowrra import Flowrra
    from flowrra.ui.django import get_urls

    # Create Flowrra instance (typically in settings or AppConfig)
    flowrra = Flowrra.from_urls()

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

WebSocket Support (Optional):
    For real-time task updates via WebSocket, you need Django-Channels.
    Without WebSocket, the frontend falls back to polling every 15 seconds.

    1. Install Django-Channels:
        pip install channels channels-redis

    2. Import the WebSocket consumer:
        from flowrra.ui.django_websocket import FlowrraConsumer, websocket_urlpatterns

    3. Configure ASGI in settings.py:
        ASGI_APPLICATION = 'your_project.asgi.application'
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels_redis.core.RedisChannelLayer',
                'CONFIG': {'hosts': [('127.0.0.1', 6379)]},
            },
        }

    4. Create/update your routing.py (or asgi.py):
        from channels.routing import ProtocolTypeRouter, URLRouter
        from django.core.asgi import get_asgi_application
        from flowrra.ui.django_websocket import websocket_urlpatterns

        application = ProtocolTypeRouter({
            'http': get_asgi_application(),
            'websocket': URLRouter(websocket_urlpatterns),
        })

    5. Deploy with ASGI server (daphne or uvicorn):
        daphne -b 0.0.0.0 -p 8000 your_project.asgi:application
        # or
        uvicorn your_project.asgi:application --host 0.0.0.0 --port 8000
"""

from typing import List
import asyncio

try:
    from django.http import JsonResponse, HttpRequest, HttpResponse, Http404
    from django.shortcuts import render
    from django.urls import path
    from django.views.decorators.csrf import csrf_exempt
    from django.views.decorators.http import require_http_methods
    import json
except ImportError:
    raise ImportError(
        "Django is required for the Django adapter. "
        "Install it with: pip install flowrra[ui-django]"
    )

from flowrra.ui.base import BaseUIAdapter


def async_to_sync_view(async_func):
    """Decorator to convert async view function to sync for Django."""
    def sync_wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                return future.result()
        else:
            return asyncio.run(async_func(*args, **kwargs))

    # Preserve function metadata
    sync_wrapper.__name__ = async_func.__name__
    sync_wrapper.__doc__ = async_func.__doc__
    return sync_wrapper


class DjangoAdapter(BaseUIAdapter):
    """Django adapter for Flowrra UI.

    This adapter provides Django views and URL patterns with HTML pages and JSON
    API endpoints for monitoring and managing Flowrra tasks and schedules.

    Routes:
        GET /                       - Dashboard page
        GET /tasks/                 - Tasks page
        GET /schedules/             - Schedules page
        GET /api/stats/             - System statistics (JSON)
        GET /api/health/            - Health check (JSON)
        GET /api/tasks/             - List registered tasks (JSON)
        GET /api/tasks/<name>/      - Get task info (JSON)
        GET /api/schedules/         - List schedules (JSON)
        POST /api/schedules/cron/   - Create schedule (JSON)
        PUT /api/schedules/<id>/enable/   - Enable schedule (JSON)
        PUT /api/schedules/<id>/disable/  - Disable schedule (JSON)
        DELETE /api/schedules/<id>/ - Delete schedule (JSON)

    Example:
        from flowrra.ui.django import get_urls
        adapter = DjangoAdapter(flowrra_app)
        urlpatterns = adapter.get_routes()
    """

    def __init__(self, flowrra_app):
        """Initialize Django adapter.

        Args:
            flowrra_app: Flowrra application instance
        """
        super().__init__(flowrra_app)

    def get_routes(self) -> List:
        """Return Django URL patterns.

        Returns:
            List of Django URL patterns
        """
        # ========================================
        # HTML Pages
        # ========================================

        @async_to_sync_view
        async def dashboard(request: HttpRequest) -> HttpResponse:
            """Render dashboard page."""
            data = await self.get_dashboard_data()
            data['format_datetime'] = self.format_datetime
            data['format_duration'] = self.format_duration
            data['get_status_color'] = self.get_status_color
            return render(request, 'django/dashboard.html', data)

        @async_to_sync_view
        async def tasks_page(request: HttpRequest) -> HttpResponse:
            """Render tasks page."""
            status = request.GET.get('status')
            data = await self.get_tasks_page_data(status=status)
            data['format_datetime'] = self.format_datetime
            data['format_duration'] = self.format_duration
            data['get_status_color'] = self.get_status_color
            return render(request, 'django/tasks.html', data)

        @async_to_sync_view
        async def schedules_page(request: HttpRequest) -> HttpResponse:
            """Render schedules page."""
            enabled_only = request.GET.get('enabled_only', 'false').lower() == 'true'
            data = await self.get_schedules_page_data(enabled_only=enabled_only)
            data['format_datetime'] = self.format_datetime
            data['format_duration'] = self.format_duration
            data['get_status_color'] = self.get_status_color
            return render(request, 'django/schedules.html', data)

        # ========================================
        # API Endpoints (JSON)
        # ========================================

        @async_to_sync_view
        async def api_stats(request: HttpRequest) -> JsonResponse:
            """Get system statistics."""
            stats = await self.get_stats()
            return JsonResponse(stats)

        @async_to_sync_view
        async def api_health(request: HttpRequest) -> JsonResponse:
            """Health check endpoint."""
            health = await self.health_check()
            return JsonResponse(health)

        @async_to_sync_view
        async def api_tasks_list(request: HttpRequest) -> JsonResponse:
            """List all registered tasks."""
            tasks = await self.list_tasks()
            return JsonResponse(tasks, safe=False)

        @async_to_sync_view
        async def api_task_detail(request: HttpRequest, task_name: str) -> JsonResponse:
            """Get specific task information."""
            task_info = await self.get_task(task_name)
            if task_info is None:
                raise Http404("Task not found")
            return JsonResponse(task_info)

        @async_to_sync_view
        async def api_schedules_list(request: HttpRequest) -> JsonResponse:
            """List all schedules."""
            enabled_only = request.GET.get('enabled_only', 'false').lower() == 'true'
            schedules = await self.list_schedules(enabled_only=enabled_only)
            return JsonResponse(schedules, safe=False)

        @async_to_sync_view
        async def api_schedule_detail(request: HttpRequest, schedule_id: str) -> JsonResponse:
            """Get specific schedule information."""
            schedule = await self.get_schedule(schedule_id)
            if schedule is None:
                raise Http404("Schedule not found")
            return JsonResponse(schedule)

        @csrf_exempt
        @require_http_methods(["POST"])
        @async_to_sync_view
        async def api_create_schedule_cron(request: HttpRequest) -> JsonResponse:
            """Create a new cron schedule."""
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            try:
                result = await self.create_schedule_cron(
                    task_name=data.get('task_name'),
                    cron=data.get('cron'),
                    args=tuple(data.get('args', [])),
                    kwargs=data.get('kwargs'),
                    enabled=data.get('enabled', True),
                    description=data.get('description'),
                    priority=data.get('priority', 0),
                )
                return JsonResponse(result, status=201)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)

        @csrf_exempt
        @require_http_methods(["PUT"])
        @async_to_sync_view
        async def api_enable_schedule(request: HttpRequest, schedule_id: str) -> JsonResponse:
            """Enable a schedule."""
            try:
                result = await self.enable_schedule(schedule_id)
                return JsonResponse(result)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)

        @csrf_exempt
        @require_http_methods(["PUT"])
        @async_to_sync_view
        async def api_disable_schedule(request: HttpRequest, schedule_id: str) -> JsonResponse:
            """Disable a schedule."""
            try:
                result = await self.disable_schedule(schedule_id)
                return JsonResponse(result)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)

        @csrf_exempt
        @require_http_methods(["DELETE"])
        @async_to_sync_view
        async def api_delete_schedule(request: HttpRequest, schedule_id: str) -> JsonResponse:
            """Delete a schedule."""
            try:
                result = await self.delete_schedule(schedule_id)
                return JsonResponse(result)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)

        # ========================================
        # URL Patterns
        # ========================================

        urlpatterns = [
            # HTML Pages
            path('', dashboard, name='flowrra_dashboard'),
            path('tasks/', tasks_page, name='flowrra_tasks'),
            path('schedules/', schedules_page, name='flowrra_schedules'),

            # API Endpoints
            path('api/stats/', api_stats, name='flowrra_api_stats'),
            path('api/health/', api_health, name='flowrra_api_health'),
            path('api/tasks/', api_tasks_list, name='flowrra_api_tasks_list'),
            path('api/tasks/<str:task_name>/', api_task_detail, name='flowrra_api_task_detail'),
            path('api/schedules/', api_schedules_list, name='flowrra_api_schedules_list'),
            path('api/schedules/<str:schedule_id>/', api_schedule_detail, name='flowrra_api_schedule_detail'),
            path('api/schedules/cron/', api_create_schedule_cron, name='flowrra_api_create_schedule'),
            path('api/schedules/<str:schedule_id>/enable/', api_enable_schedule, name='flowrra_api_enable_schedule'),
            path('api/schedules/<str:schedule_id>/disable/', api_disable_schedule, name='flowrra_api_disable_schedule'),
        ]

        return urlpatterns


def get_urls(flowrra_app) -> List:
    """Get Django URL patterns for Flowrra UI.

    This is a convenience function for quick setup.

    Args:
        flowrra_app: Flowrra application instance

    Returns:
        List of Django URL patterns ready to be included

    Example:
        from django.urls import path, include
        from flowrra import Flowrra
        from flowrra.ui.django import get_urls

        flowrra = Flowrra.from_urls()

        urlpatterns = [
            path('flowrra/', include(get_urls(flowrra))),
        ]
    """
    adapter = DjangoAdapter(flowrra_app)
    return adapter.get_routes()
