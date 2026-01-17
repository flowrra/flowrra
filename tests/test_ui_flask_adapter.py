"""Tests for Flask/Quart UI adapter."""

import pytest

# Check if Quart is available
quart_available = True
try:
    from quart import Quart
    from flowrra.ui.flask import FlaskAdapter, create_blueprint
except ImportError:
    quart_available = False

from flowrra import Flowrra, Config, ExecutorConfig

pytestmark = pytest.mark.skipif(
    not quart_available,
    reason="Quart not installed (pip install flowrra[ui-flask])"
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
def quart_app(app):
    """Create Quart app with Flowrra blueprint registered."""
    quart_app = Quart(__name__)
    quart_app.config["TESTING"] = True

    blueprint = create_blueprint(app)
    quart_app.register_blueprint(blueprint, url_prefix="/flowrra")

    return quart_app


@pytest.fixture
def client(quart_app):
    """Create test client."""
    return quart_app.test_client()


class TestAdapterCreation:
    """Test adapter initialization."""

    def test_adapter_creation(self, app):
        """Test creating Flask adapter."""
        adapter = FlaskAdapter(app)
        assert adapter.flowrra is app
        assert adapter.manager is not None

    def test_adapter_has_templates_dir(self, app):
        """Test adapter has templates directory configured."""
        adapter = FlaskAdapter(app)
        assert adapter.templates_dir.exists()

    def test_get_routes_returns_blueprint(self, app):
        """Test get_routes returns Blueprint."""
        from quart import Blueprint

        adapter = FlaskAdapter(app)
        blueprint = adapter.get_routes()
        assert isinstance(blueprint, Blueprint)

    def test_create_blueprint_helper(self, app):
        """Test create_blueprint convenience function."""
        from quart import Blueprint

        blueprint = create_blueprint(app)
        assert isinstance(blueprint, Blueprint)

    def test_blueprint_has_static_folder(self, app):
        """Test blueprint has static folder configured."""
        adapter = FlaskAdapter(app)
        blueprint = adapter.get_routes()
        assert blueprint.static_folder is not None


class TestHTMLPages:
    """Test HTML page routes."""

    @pytest.mark.asyncio
    async def test_dashboard_page(self, client, running_app):
        """Test dashboard page renders."""
        response = await client.get("/flowrra/")
        assert response.status_code == 200
        data = await response.get_data()
        assert b"Dashboard" in data

    @pytest.mark.asyncio
    async def test_tasks_page(self, client, running_app):
        """Test tasks page renders."""
        response = await client.get("/flowrra/tasks")
        assert response.status_code == 200
        data = await response.get_data()
        assert b"Tasks" in data

    @pytest.mark.asyncio
    async def test_tasks_page_with_status_filter(self, client, running_app):
        """Test tasks page with status filter."""
        for status in ["pending", "running", "success", "failed"]:
            response = await client.get(f"/flowrra/tasks?status={status}")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_schedules_page(self, client, running_app):
        """Test schedules page renders."""
        response = await client.get("/flowrra/schedules")
        assert response.status_code == 200
        data = await response.get_data()
        assert b"Schedules" in data

    @pytest.mark.asyncio
    async def test_schedules_page_with_enabled_filter(self, client, running_app):
        """Test schedules page with enabled_only filter."""
        response = await client.get("/flowrra/schedules?enabled_only=true")
        assert response.status_code == 200


class TestAPIEndpoints:
    """Test JSON API endpoints."""

    @pytest.mark.asyncio
    async def test_api_stats(self, client, running_app):
        """Test API stats endpoint."""
        response = await client.get("/flowrra/api/stats")
        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = await response.get_json()
        assert "app" in data
        assert "executors" in data
        assert "tasks" in data

    @pytest.mark.asyncio
    async def test_api_health(self, client, running_app):
        """Test API health endpoint."""
        response = await client.get("/flowrra/api/health")
        assert response.status_code == 200

        data = await response.get_json()
        assert "healthy" in data
        assert "timestamp" in data
        assert "components" in data

    @pytest.mark.asyncio
    async def test_api_list_tasks(self, client, running_app):
        """Test API list tasks endpoint."""
        response = await client.get("/flowrra/api/tasks")
        assert response.status_code == 200

        data = await response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]

    @pytest.mark.asyncio
    async def test_api_get_task_existing(self, client, running_app):
        """Test API get task endpoint with existing task."""
        response = await client.get("/flowrra/api/tasks/test_task")
        assert response.status_code == 200

        data = await response.get_json()
        assert data["name"] == "test_task"

    @pytest.mark.asyncio
    async def test_api_get_task_nonexistent(self, client, running_app):
        """Test API get task endpoint with non-existent task."""
        response = await client.get("/flowrra/api/tasks/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_api_list_schedules(self, client, running_app):
        """Test API list schedules endpoint."""
        response = await client.get("/flowrra/api/schedules")
        assert response.status_code == 200

        data = await response.get_json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_api_list_schedules_enabled_only(self, client, running_app):
        """Test API list schedules with enabled_only filter."""
        response = await client.get("/flowrra/api/schedules?enabled_only=true")
        assert response.status_code == 200

        data = await response.get_json()
        assert isinstance(data, list)


class TestStaticFiles:
    """Test static file paths."""

    def test_css_file_exists(self, app):
        """Test CSS file exists."""
        adapter = FlaskAdapter(app)
        css_file = adapter.static_dir / "style.css"
        assert css_file.exists()

    def test_js_file_exists(self, app):
        """Test JavaScript file exists."""
        adapter = FlaskAdapter(app)
        js_file = adapter.static_dir / "app.js"
        assert js_file.exists()

    def test_static_dir_property(self, app):
        """Test static_dir property returns correct path."""
        adapter = FlaskAdapter(app)
        assert adapter.static_dir.exists()
        assert adapter.static_dir.is_dir()


class TestTemplateIntegration:
    """Test template rendering with real data."""

    @pytest.mark.asyncio
    async def test_dashboard_shows_stats(self, client, running_app):
        """Test dashboard displays system stats."""
        response = await client.get("/flowrra/")
        data = await response.get_data()
        content = data.decode()

        # Check for key elements
        assert "Running" in content or "Stopped" in content
        assert "IO Executor" in content
        assert "Registered Tasks" in content

    @pytest.mark.asyncio
    async def test_tasks_page_shows_registered_tasks(self, client, running_app):
        """Test tasks page shows registered tasks."""
        response = await client.get("/flowrra/tasks")
        data = await response.get_data()
        content = data.decode()

        # Should show our test tasks
        assert "test_task" in content
        assert "retry_task" in content

    @pytest.mark.asyncio
    async def test_tasks_page_shows_task_types(self, client, running_app):
        """Test tasks page shows task types (IO/CPU)."""
        response = await client.get("/flowrra/tasks")
        data = await response.get_data()
        content = data.decode()

        # Should indicate IO-bound
        assert "IO-bound" in content


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_404_for_invalid_task(self, client, running_app):
        """Test 404 response for non-existent task."""
        response = await client.get("/flowrra/api/tasks/invalid_task_name")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_404_for_invalid_schedule(self, client, running_app):
        """Test 404 response for non-existent schedule."""
        response = await client.get("/flowrra/api/schedules/invalid_schedule_id")
        assert response.status_code == 404


class TestBlueprintConfiguration:
    """Test blueprint configuration options."""

    def test_blueprint_name(self, app):
        """Test blueprint has correct name."""
        adapter = FlaskAdapter(app)
        blueprint = adapter.get_routes()
        assert blueprint.name == "flowrra"

    @pytest.mark.asyncio
    async def test_blueprint_with_custom_prefix(self, app):
        """Test registering blueprint with custom prefix."""
        from quart import Quart
        quart_app = Quart(__name__)
        quart_app.config["TESTING"] = True

        blueprint = create_blueprint(app)
        quart_app.register_blueprint(blueprint, url_prefix="/custom-path")

        client = quart_app.test_client()
        # Blueprint should not be accessible at /flowrra/
        response = await client.get("/flowrra/")
        assert response.status_code == 404

    def test_template_filters_registered(self, app):
        """Test template filters are registered."""
        from quart import Quart
        quart_app = Quart(__name__)
        blueprint = create_blueprint(app)
        quart_app.register_blueprint(blueprint)

        # Filters should be available in Jinja environment
        # Note: Quart registers filters at blueprint registration time


class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.asyncio
    async def test_full_ui_workflow(self, client, running_app):
        """Test complete UI workflow."""
        # 1. Access dashboard
        response = await client.get("/flowrra/")
        assert response.status_code == 200

        # 2. Check API stats
        response = await client.get("/flowrra/api/stats")
        assert response.status_code == 200
        stats = await response.get_json()
        assert stats["app"]["running"] is True

        # 3. View tasks page
        response = await client.get("/flowrra/tasks")
        assert response.status_code == 200

        # 4. Get task info via API
        response = await client.get("/flowrra/api/tasks/test_task")
        assert response.status_code == 200

        # 5. Health check
        response = await client.get("/flowrra/api/health")
        assert response.status_code == 200
        health = await response.get_json()
        assert health["healthy"] is True

    @pytest.mark.asyncio
    async def test_adapter_with_stopped_app(self, client, app):
        """Test UI works with stopped app."""
        # App is not started
        response = await client.get("/flowrra/")
        assert response.status_code == 200

        # Stats should show app not running
        response = await client.get("/flowrra/api/stats")
        assert response.status_code == 200
        stats = await response.get_json()
        assert stats["app"]["running"] is False


class TestMounting:
    """Test mounting at different paths."""

    @pytest.mark.asyncio
    async def test_mount_at_root(self, app):
        """Test mounting blueprint at application root."""
        from quart import Quart
        quart_app = Quart(__name__)
        quart_app.config["TESTING"] = True

        blueprint = create_blueprint(app)
        quart_app.register_blueprint(blueprint)

        client = quart_app.test_client()
        response = await client.get("/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_mount_at_custom_prefix(self, app):
        """Test mounting blueprint at custom prefix."""
        from quart import Quart
        quart_app = Quart(__name__)
        quart_app.config["TESTING"] = True

        blueprint = create_blueprint(app)
        quart_app.register_blueprint(blueprint, url_prefix="/custom-path")

        client = quart_app.test_client()
        response = await client.get("/custom-path/")
        assert response.status_code == 200
