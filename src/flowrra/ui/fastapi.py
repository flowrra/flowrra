"""FastAPI adapter for Flowrra UI.

This module provides a FastAPI router that can be mounted into existing
FastAPI applications to add Flowrra's management interface.

Installation:
    pip install flowrra[ui-fastapi]

Example:
    from fastapi import FastAPI
    from flowrra import Flowrra
    from flowrra.ui.fastapi import create_router

    app = FastAPI()
    flowrra = Flowrra.from_urls()

    # Mount Flowrra UI
    app.include_router(
        create_router(flowrra),
        prefix="/flowrra",
        tags=["flowrra"]
    )

    @app.on_event("startup")
    async def startup():
        await flowrra.start()

    @app.on_event("shutdown")
    async def shutdown():
        await flowrra.stop()
"""

from typing import Optional
from pathlib import Path
import asyncio
import logging

try:
    from fastapi import APIRouter, Request, HTTPException
    from fastapi import WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.templating import Jinja2Templates
    from pydantic import BaseModel
except ImportError:
    raise ImportError(
        "FastAPI is required for the FastAPI adapter. "
        "Install it with: pip install flowrra[ui-fastapi]"
    )

from flowrra.ui.base import BaseUIAdapter
from flowrra.events import event_bus

logger = logging.getLogger(__name__)


class CreateScheduleRequest(BaseModel):
    """Request model for creating a cron schedule."""
    task_name: str
    cron: str
    args: tuple = ()
    kwargs: Optional[dict] = None
    enabled: bool = True
    description: Optional[str] = None
    priority: int = 0


class FastAPIAdapter(BaseUIAdapter):
    """FastAPI adapter for Flowrra UI.

    This adapter provides a FastAPI router with HTML pages and JSON API endpoints
    for monitoring and managing Flowrra tasks and schedules.

    Routes:
        GET /                       - Dashboard page
        GET /tasks                  - Tasks page
        GET /schedules              - Schedules page
        GET /api/stats              - System statistics (JSON)
        GET /api/health             - Health check (JSON)
        GET /api/tasks              - List registered tasks (JSON)
        GET /api/tasks/{name}       - Get task info (JSON)
        GET /api/schedules          - List schedules (JSON)
        POST /api/schedules         - Create schedule (JSON)
        PUT /api/schedules/{id}     - Update schedule (JSON)
        DELETE /api/schedules/{id}  - Delete schedule (JSON)

    Example:
        adapter = FastAPIAdapter(flowrra_app)
        router = adapter.get_routes()
        app.include_router(router, prefix="/flowrra")
    """

    def __init__(self, flowrra_app):
        """Initialize FastAPI adapter.

        Args:
            flowrra_app: Flowrra application instance
        """
        super().__init__(flowrra_app)

        self.templates = Jinja2Templates(directory=str(self.templates_dir))

        self.templates.env.filters["format_datetime"] = self.format_datetime
        self.templates.env.filters["format_duration"] = self.format_duration
        self.templates.env.filters["status_color"] = self.get_status_color

    def get_routes(self) -> APIRouter:
        """Return FastAPI router with all routes.

        Returns:
            APIRouter instance with HTML and API routes
        """
        router = APIRouter()

        # ========================================
        # HTML Pages
        # ========================================

        @router.websocket("/ws")
        async def websocket(ws: WebSocket):
            """WebSocket endpoint for events."""
            await ws.accept()
            queue: asyncio.Queue[dict] = asyncio.Queue()

            async def subscriber(event : dict):
                await queue.put(event)

            event_bus.subscribe(subscriber)

            try:
                while True:
                    event = await queue.get()
                    await ws.send_json(event)
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
            finally:
                event_bus._subscribers.remove(subscriber)

        @router.get("/", response_class=HTMLResponse, name="dashboard")
        async def dashboard(request: Request):
            """Render dashboard page."""
            data = await self.get_dashboard_data()
            return self.templates.TemplateResponse(
                name="dashboard.html",
                context={"request": request, **data},
            )

        @router.get("/tasks", response_class=HTMLResponse, name="tasks")
        async def tasks_page(
            request: Request,
            status: Optional[str] = None,
            limit: int = 200
        ):
            """Render tasks page.

            Args:
                status: Optional status filter (pending/running/success/failed)
                limit: Maximum number of tasks to display (default: 200)
            """
            data = await self.get_tasks_page_data(status=status, limit=limit)
            return self.templates.TemplateResponse(
                name="tasks.html",
                context={"request": request, **data},
            )

        @router.get("/schedules", response_class=HTMLResponse, name="schedules")
        async def schedules_page(
            request: Request, enabled_only: bool = False
        ):
            """Render schedules page.

            Args:
                enabled_only: If True, only show enabled schedules
            """
            data = await self.get_schedules_page_data(enabled_only=enabled_only)
            return self.templates.TemplateResponse(
                name="schedules.html",
                context={"request": request, **data},
            )

        # ========================================
        # API Endpoints (JSON)
        # ========================================

        @router.get("/api/stats", response_class=JSONResponse, name="api_stats")
        async def api_stats():
            """Get system statistics."""
            return await self.get_stats()

        @router.get("/api/health", response_class=JSONResponse, name="api_health")
        async def api_health():
            """Health check endpoint."""
            return await self.health_check()

        @router.get("/api/tasks", response_class=JSONResponse, name="api_tasks_list")
        async def api_tasks_list():
            """List all registered tasks."""
            return await self.list_tasks()

        @router.get(
            "/api/tasks/{task_name}",
            response_class=JSONResponse,
            name="api_task_detail",
        )
        async def api_task_detail(task_name: str):
            """Get specific task information."""
            task_info = await self.get_task(task_name)
            if task_info is None:
                raise HTTPException(status_code=404, detail="Task not found")
            return task_info

        @router.get(
            "/api/schedules",
            response_class=JSONResponse,
            name="api_schedules_list",
        )
        async def api_schedules_list(enabled_only: bool = False):
            """List all schedules.

            Args:
                enabled_only: If True, only return enabled schedules
            """
            return await self.list_schedules(enabled_only=enabled_only)

        @router.get(
            "/api/schedules/{schedule_id}",
            response_class=JSONResponse,
            name="api_schedule_detail",
        )
        async def api_schedule_detail(schedule_id: str):
            """Get specific schedule information."""
            schedule = await self.get_schedule(schedule_id)
            if schedule is None:
                raise HTTPException(status_code=404, detail="Schedule not found")
            return schedule

        @router.post(
            "/api/schedules/cron",
            response_class=JSONResponse,
            name="api_create_schedule",
        )
        async def api_create_schedule_cron(request: CreateScheduleRequest):
            """Create a new cron schedule."""
            return await self.create_schedule_cron(
                task_name=request.task_name,
                cron=request.cron,
                args=request.args,
                kwargs=request.kwargs,
                enabled=request.enabled,
                description=request.description,
                priority=request.priority,
            )

        @router.put(
            "/api/schedules/{schedule_id}/enable",
            response_class=JSONResponse,
            name="api_enable_schedule",
        )
        async def api_enable(schedule_id: str):
            """Enable a schedule."""
            return await self.enable_schedule(schedule_id)

        @router.put(
            "/api/schedules/{schedule_id}/disable",
            response_class=JSONResponse,
            name="api_disable_schedule",
        )
        async def api_disable(schedule_id: str):
            """Disable a schedule."""
            return await self.disable_schedule(schedule_id)

        @router.delete(
            "/api/schedules/{schedule_id}",
            response_class=JSONResponse,
            name="api_delete_schedule",
        )
        async def api_delete(schedule_id: str):
            """Delete a schedule."""
            return await self.delete_schedule(schedule_id)

        # ========================================
        # Static Files
        # ========================================

        @router.get("/static/{file_path:path}", name="static_files")
        async def serve_static(file_path: str):
            """Serve static files (CSS, JS, images)."""
            static_file = self.static_dir / file_path
            if static_file.exists() and static_file.is_file():
                return FileResponse(static_file)
            raise HTTPException(status_code=404, detail="File not found")

        return router


def create_router(flowrra_app) -> APIRouter:
    """Create FastAPI router for Flowrra UI.

    This is a convenience function for quick setup.

    Args:
        flowrra_app: Flowrra application instance

    Returns:
        APIRouter instance ready to be included in FastAPI app

    Example:
        from fastapi import FastAPI
        from flowrra import Flowrra
        from flowrra.ui.fastapi import create_router

        app = FastAPI()
        flowrra = Flowrra.from_urls()

        app.include_router(
            create_router(flowrra),
            prefix="/flowrra",
            tags=["flowrra"]
        )
    """
    adapter = FastAPIAdapter(flowrra_app)
    return adapter.get_routes()
