"""Flask/Quart adapter for Flowrra UI.

This module provides a Flask/Quart Blueprint that can be registered in existing
Flask or Quart applications to add Flowrra's management interface.

Installation:
    pip install flowrra[ui-flask]  # For Flask (async support via Quart)

Example (Quart - Recommended for async):
    from quart import Quart
    from flowrra import Flowrra
    from flowrra.ui.flask import create_blueprint

    app = Quart(__name__)
    flowrra = Flowrra.from_urls()

    # Register Flowrra UI blueprint
    app.register_blueprint(
        create_blueprint(flowrra),
        url_prefix="/flowrra"
    )

    @app.before_serving
    async def startup():
        await flowrra.start()

Example (Flask - Traditional):
    from flask import Flask
    from flowrra import Flowrra
    from flowrra.ui.flask import create_blueprint

    app = Flask(__name__)
    flowrra = Flowrra.from_urls()

    app.register_blueprint(
        create_blueprint(flowrra),
        url_prefix="/flowrra"
    )

WebSocket Support (Optional):
    For real-time task updates via WebSocket, use Quart and setup WebSocket endpoint.
    Without WebSocket, the frontend falls back to polling every 15 seconds.

    from quart import Quart
    from flowrra import Flowrra
    from flowrra.ui.flask import create_blueprint
    from flowrra.ui.quart_websocket import setup_websocket

    app = Quart(__name__)
    flowrra = Flowrra.from_urls()

    # Register UI blueprint
    app.register_blueprint(create_blueprint(flowrra), url_prefix="/flowrra")

    # Setup WebSocket endpoint at /flowrra/ws
    setup_websocket(app)

    @app.before_serving
    async def startup():
        await flowrra.start()

    # Deploy with ASGI server
    # hypercorn app:app --bind 0.0.0.0:8000
    # or: uvicorn app:app --host 0.0.0.0 --port 8000

    See docs/WEBSOCKET_SETUP.md for detailed configuration guide.
"""

from typing import Optional

try:
    # Try Quart first (async-native Flask alternative)
    from quart import Blueprint, render_template, request, jsonify
    USING_QUART = True
except ImportError:
    USING_QUART = False
    try:
        # Fall back to Flask
        from flask import Blueprint, render_template, request, jsonify
    except ImportError:
        raise ImportError(
            "Flask or Quart is required for the Flask adapter. "
            "Install with: pip install flowrra[ui-flask]"
        )

from flowrra.ui.base import BaseUIAdapter


class FlaskAdapter(BaseUIAdapter):
    """Flask/Quart adapter for Flowrra UI.

    This adapter provides a Flask/Quart Blueprint with HTML pages and JSON API endpoints
    for monitoring and managing Flowrra tasks and schedules. Works with both Quart (async)
    and Flask (traditional).

    Routes:
        GET /                       - Dashboard page
        GET /tasks                  - Tasks page
        GET /schedules              - Schedules page
        GET /api/stats              - System statistics (JSON)
        GET /api/health             - Health check (JSON)
        GET /api/tasks              - List registered tasks (JSON)
        GET /api/tasks/<name>       - Get task info (JSON)
        GET /api/schedules          - List schedules (JSON)
        POST /api/schedules/cron    - Create schedule (JSON)
        PUT /api/schedules/<id>/enable   - Enable schedule (JSON)
        PUT /api/schedules/<id>/disable  - Disable schedule (JSON)
        DELETE /api/schedules/<id>  - Delete schedule (JSON)

    Example (Quart):
        from quart import Quart
        adapter = FlaskAdapter(flowrra_app)
        blueprint = adapter.get_routes()
        app = Quart(__name__)
        app.register_blueprint(blueprint, url_prefix="/flowrra")

    Example (Flask):
        from flask import Flask
        adapter = FlaskAdapter(flowrra_app)
        blueprint = adapter.get_routes()
        app = Flask(__name__)
        app.register_blueprint(blueprint, url_prefix="/flowrra")
    """

    def __init__(self, flowrra_app):
        """Initialize Flask adapter.

        Args:
            flowrra_app: Flowrra application instance
        """
        super().__init__(flowrra_app)

    def get_routes(self) -> Blueprint:
        """Return Flask Blueprint with all routes.

        Returns:
            Blueprint instance with HTML and API routes
        """
        blueprint = Blueprint(
            "flowrra",
            __name__,
            template_folder=str(self.templates_dir),
            static_folder=str(self.static_dir),
            static_url_path="/static",
        )

        blueprint.add_app_template_filter(self.format_datetime, "format_datetime")
        blueprint.add_app_template_filter(self.format_duration, "format_duration")
        blueprint.add_app_template_filter(self.get_status_color, "status_color")

        # ========================================
        # HTML Pages
        # ========================================

        @blueprint.route("/", methods=["GET"])
        async def dashboard():
            """Render dashboard page."""
            data = await self.get_dashboard_data()
            if USING_QUART:
                return await render_template("dashboard.html", **data)
            else:
                return render_template("dashboard.html", **data)

        @blueprint.route("/tasks", methods=["GET"])
        async def tasks_page():
            """Render tasks page."""
            status = request.args.get("status")
            limit = int(request.args.get("limit", 200))
            data = await self.get_tasks_page_data(status=status, limit=limit)
            if USING_QUART:
                return await render_template("tasks.html", **data)
            else:
                return render_template("tasks.html", **data)

        @blueprint.route("/schedules", methods=["GET"])
        async def schedules_page():
            """Render schedules page."""
            enabled_only = request.args.get("enabled_only", "false").lower() == "true"
            data = await self.get_schedules_page_data(enabled_only=enabled_only)
            if USING_QUART:
                return await render_template("schedules.html", **data)
            else:
                return render_template("schedules.html", **data)

        # ========================================
        # API Endpoints (JSON)
        # ========================================

        @blueprint.route("/api/stats", methods=["GET"])
        async def api_stats():
            """Get system statistics."""
            stats = await self.get_stats()
            return jsonify(stats)

        @blueprint.route("/api/health", methods=["GET"])
        async def api_health():
            """Health check endpoint."""
            health = await self.health_check()
            return jsonify(health)

        @blueprint.route("/api/tasks", methods=["GET"])
        async def api_tasks_list():
            """List all registered tasks."""
            tasks = await self.list_tasks()
            return jsonify(tasks)

        @blueprint.route("/api/tasks/<task_name>", methods=["GET"])
        async def api_task_detail(task_name: str):
            """Get specific task information."""
            task_info = await self.get_task(task_name)
            if task_info is None:
                return jsonify({"error": "Task not found"}), 404
            return jsonify(task_info)

        @blueprint.route("/api/schedules", methods=["GET"])
        async def api_schedules_list():
            """List all schedules."""
            enabled_only = request.args.get("enabled_only", "false").lower() == "true"
            schedules = await self.list_schedules(enabled_only=enabled_only)
            return jsonify(schedules)

        @blueprint.route("/api/schedules/<schedule_id>", methods=["GET"])
        async def api_schedule_detail(schedule_id: str):
            """Get specific schedule information."""
            schedule = await self.get_schedule(schedule_id)
            if schedule is None:
                return jsonify({"error": "Schedule not found"}), 404
            return jsonify(schedule)

        @blueprint.route("/api/schedules/cron", methods=["POST"])
        async def api_create_schedule_cron():
            """Create a new cron schedule."""
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body required"}), 400

            try:
                result = await self.create_schedule_cron(
                    task_name=data.get("task_name"),
                    cron=data.get("cron"),
                    args=tuple(data.get("args", [])),
                    kwargs=data.get("kwargs"),
                    enabled=data.get("enabled", True),
                    description=data.get("description"),
                    priority=data.get("priority", 0),
                )
                return jsonify(result), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @blueprint.route("/api/schedules/<schedule_id>/enable", methods=["PUT"])
        async def api_enable(schedule_id: str):
            """Enable a schedule."""
            try:
                result = await self.enable_schedule(schedule_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @blueprint.route("/api/schedules/<schedule_id>/disable", methods=["PUT"])
        async def api_disable(schedule_id: str):
            """Disable a schedule."""
            try:
                result = await self.disable_schedule(schedule_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @blueprint.route("/api/schedules/<schedule_id>", methods=["DELETE"])
        async def api_delete(schedule_id: str):
            """Delete a schedule."""
            try:
                result = await self.delete_schedule(schedule_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        return blueprint


def create_blueprint(flowrra_app) -> Blueprint:
    """Create Flask Blueprint for Flowrra UI.

    This is a convenience function for quick setup.

    Args:
        flowrra_app: Flowrra application instance

    Returns:
        Blueprint instance ready to be registered in Flask app

    Example:
        from flask import Flask
        from flowrra import Flowrra
        from flowrra.ui.flask import create_blueprint

        app = Flask(__name__)
        flowrra = Flowrra.from_urls()

        app.register_blueprint(
            create_blueprint(flowrra),
            url_prefix="/flowrra"
        )
    """
    adapter = FlaskAdapter(flowrra_app)
    return adapter.get_routes()
