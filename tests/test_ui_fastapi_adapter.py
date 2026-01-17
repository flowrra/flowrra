"""Tests for FastAPI UI adapter."""

import pytest
from pathlib import Path

# Check if FastAPI is available
fastapi_available = True
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from flowrra.ui.fastapi import FastAPIAdapter, create_router
except ImportError:
    fastapi_available = False

from flowrra import Flowrra, Config, ExecutorConfig

pytestmark = pytest.mark.skipif(
    not fastapi_available,
    reason="FastAPI not installed (pip install flowrra[ui-fastapi])"
)


@pytest.fixture
def app():
    """Create Flowrra app."""
    config = Config(executor=ExecutorConfig(num_workers=2))
    app = Flowrra(config=config)

    @app.task()
    async def test_task(x: int):
        """Test IO-bound task."""
        return x * 2

    @app.task(max_retries=3)
    async def retry_task(n: int):
        """Test task with retries."""
        return n + 1

    return app


@pytest.fixture
async def running_app(app):
    """Create and start Flowrra app."""
    await app.start()
    yield app
    await app.stop()


@pytest.fixture
def fastapi_app(app):
    """Create FastAPI app with Flowrra router mounted."""
    fastapi_app = FastAPI()
    router = create_router(app)
    fastapi_app.include_router(router, prefix="/flowrra")
    return fastapi_app


@pytest.fixture
def client(fastapi_app):
    """Create test client."""
    return TestClient(fastapi_app)


class TestAdapterCreation:
    """Test adapter initialization."""

    def test_adapter_creation(self, app):
        """Test creating FastAPI adapter."""
        adapter = FastAPIAdapter(app)
        assert adapter.flowrra is app
        assert adapter.manager is not None

    def test_adapter_has_templates(self, app):
        """Test adapter has Jinja2 templates configured."""
        adapter = FastAPIAdapter(app)
        assert adapter.templates is not None
        assert adapter.templates_dir.exists()

    def test_adapter_template_filters(self, app):
        """Test custom Jinja2 filters are registered."""
        adapter = FastAPIAdapter(app)
        env = adapter.templates.env

        # Check filters are registered
        assert "format_datetime" in env.filters
        assert "format_duration" in env.filters
        assert "status_color" in env.filters

    def test_get_routes_returns_router(self, app):
        """Test get_routes returns APIRouter."""
        from fastapi import APIRouter

        adapter = FastAPIAdapter(app)
        router = adapter.get_routes()
        assert isinstance(router, APIRouter)

    def test_create_router_helper(self, app):
        """Test create_router convenience function."""
        from fastapi import APIRouter

        router = create_router(app)
        assert isinstance(router, APIRouter)


class TestHTMLPages:
    """Test HTML page routes."""

    @pytest.mark.asyncio
    async def test_dashboard_page(self, client, running_app):
        """Test dashboard page renders."""
        response = client.get("/flowrra/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Dashboard" in response.content

    @pytest.mark.asyncio
    async def test_tasks_page(self, client, running_app):
        """Test tasks page renders."""
        response = client.get("/flowrra/tasks")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Tasks" in response.content

    @pytest.mark.asyncio
    async def test_tasks_page_with_status_filter(self, client, running_app):
        """Test tasks page with status filter."""
        for status in ["pending", "running", "success", "failed"]:
            response = client.get(f"/flowrra/tasks?status={status}")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_schedules_page(self, client, running_app):
        """Test schedules page renders."""
        response = client.get("/flowrra/schedules")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Schedules" in response.content

    @pytest.mark.asyncio
    async def test_schedules_page_with_enabled_filter(self, client, running_app):
        """Test schedules page with enabled_only filter."""
        response = client.get("/flowrra/schedules?enabled_only=true")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestAPIEndpoints:
    """Test JSON API endpoints."""

    @pytest.mark.asyncio
    async def test_api_stats(self, client, running_app):
        """Test API stats endpoint."""
        response = client.get("/flowrra/api/stats")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert "app" in data
        assert "executors" in data
        assert "tasks" in data

    @pytest.mark.asyncio
    async def test_api_health(self, client, running_app):
        """Test API health endpoint."""
        response = client.get("/flowrra/api/health")
        assert response.status_code == 200

        data = response.json()
        assert "healthy" in data
        assert "timestamp" in data
        assert "components" in data

    @pytest.mark.asyncio
    async def test_api_list_tasks(self, client, running_app):
        """Test API list tasks endpoint."""
        response = client.get("/flowrra/api/tasks")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]

    @pytest.mark.asyncio
    async def test_api_get_task_existing(self, client, running_app):
        """Test API get task endpoint with existing task."""
        response = client.get("/flowrra/api/tasks/test_task")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "test_task"

    @pytest.mark.asyncio
    async def test_api_get_task_nonexistent(self, client, running_app):
        """Test API get task endpoint with non-existent task."""
        response = client.get("/flowrra/api/tasks/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_api_list_schedules(self, client, running_app):
        """Test API list schedules endpoint."""
        response = client.get("/flowrra/api/schedules")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_api_list_schedules_enabled_only(self, client, running_app):
        """Test API list schedules with enabled_only filter."""
        response = client.get("/flowrra/api/schedules?enabled_only=true")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)


class TestStaticFiles:
    """Test static file paths."""

    def test_css_file_exists(self, app):
        """Test CSS file exists."""
        adapter = FastAPIAdapter(app)
        css_file = adapter.static_dir / "style.css"
        assert css_file.exists()

    def test_js_file_exists(self, app):
        """Test JavaScript file exists."""
        adapter = FastAPIAdapter(app)
        js_file = adapter.static_dir / "app.js"
        assert js_file.exists()

    def test_static_dir_property(self, app):
        """Test static_dir property returns correct path."""
        adapter = FastAPIAdapter(app)
        assert adapter.static_dir.exists()
        assert adapter.static_dir.is_dir()


class TestTemplateIntegration:
    """Test template rendering with real data."""

    @pytest.mark.asyncio
    async def test_dashboard_shows_stats(self, client, running_app):
        """Test dashboard displays system stats."""
        response = client.get("/flowrra/")
        content = response.content.decode()

        # Check for key elements
        assert "Running" in content or "Stopped" in content
        assert "IO Executor" in content
        assert "Registered Tasks" in content

    @pytest.mark.asyncio
    async def test_tasks_page_shows_registered_tasks(self, client, running_app):
        """Test tasks page shows registered tasks."""
        response = client.get("/flowrra/tasks")
        content = response.content.decode()

        # Should show our test tasks
        assert "test_task" in content
        assert "retry_task" in content

    @pytest.mark.asyncio
    async def test_tasks_page_shows_task_types(self, client, running_app):
        """Test tasks page shows task types (IO/CPU)."""
        response = client.get("/flowrra/tasks")
        content = response.content.decode()

        # Should indicate IO-bound
        assert "IO-bound" in content


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_404_for_invalid_task(self, client, running_app):
        """Test 404 response for non-existent task."""
        response = client.get("/flowrra/api/tasks/invalid_task_name")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_404_for_invalid_schedule(self, client, running_app):
        """Test 404 response for non-existent schedule."""
        response = client.get("/flowrra/api/schedules/invalid_schedule_id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRouteNaming:
    """Test route names are correct."""

    def test_route_names_defined(self, fastapi_app):
        """Test all routes have proper names."""
        route_names = [route.name for route in fastapi_app.routes if hasattr(route, 'name')]

        expected_names = [
            "dashboard",
            "tasks",
            "schedules",
            "api_stats",
            "api_health",
            "api_tasks_list",
            "api_task_detail",
            "api_schedules_list",
            "api_schedule_detail",
            "api_create_schedule",
            "api_enable_schedule",
            "api_disable_schedule",
            "api_delete_schedule",
        ]

        for name in expected_names:
            assert name in route_names, f"Route '{name}' not found"


class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.asyncio
    async def test_full_ui_workflow(self, client, running_app):
        """Test complete UI workflow."""
        # 1. Access dashboard
        response = client.get("/flowrra/")
        assert response.status_code == 200

        # 2. Check API stats
        response = client.get("/flowrra/api/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["app"]["running"] is True

        # 3. View tasks page
        response = client.get("/flowrra/tasks")
        assert response.status_code == 200

        # 4. Get task info via API
        response = client.get("/flowrra/api/tasks/test_task")
        assert response.status_code == 200

        # 5. Health check
        response = client.get("/flowrra/api/health")
        assert response.status_code == 200
        health = response.json()
        assert health["healthy"] is True

    @pytest.mark.asyncio
    async def test_adapter_with_stopped_app(self, client, app):
        """Test UI works with stopped app."""
        # App is not started
        response = client.get("/flowrra/")
        assert response.status_code == 200

        # Stats should show app not running
        response = client.get("/flowrra/api/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["app"]["running"] is False


class TestMounting:
    """Test mounting at different paths."""

    def test_mount_at_root(self, app):
        """Test mounting router at application root."""
        fastapi_app = FastAPI()
        router = create_router(app)
        fastapi_app.include_router(router)

        client = TestClient(fastapi_app)
        response = client.get("/")
        assert response.status_code == 200

    def test_mount_at_custom_prefix(self, app):
        """Test mounting router at custom prefix."""
        fastapi_app = FastAPI()
        router = create_router(app)
        fastapi_app.include_router(router, prefix="/custom-path")

        client = TestClient(fastapi_app)
        response = client.get("/custom-path/")
        assert response.status_code == 200

    def test_mount_with_tags(self, app):
        """Test mounting router with tags."""
        fastapi_app = FastAPI()
        router = create_router(app)
        fastapi_app.include_router(router, prefix="/flowrra", tags=["flowrra", "monitoring"])

        # Check OpenAPI schema includes tags
        client = TestClient(fastapi_app)
        response = client.get("/openapi.json")
        assert response.status_code == 200
