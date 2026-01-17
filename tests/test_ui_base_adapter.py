"""Tests for base UI adapter."""

import pytest
from pathlib import Path
from flowrra import Flowrra, Config, ExecutorConfig
from flowrra.ui.base import BaseUIAdapter


# Create a concrete implementation for testing
class DummyAdapter(BaseUIAdapter):
    """Dummy implementation of BaseUIAdapter for testing."""

    def get_routes(self):
        """Return dummy routes for testing."""
        return {"type": "test_routes"}


@pytest.fixture
def app():
    """Create Flowrra app."""
    config = Config(executor=ExecutorConfig(num_workers=2))
    app = Flowrra(config=config)

    @app.task()
    async def test_task(x: int):
        return x * 2

    return app


@pytest.fixture
async def running_app(app):
    """Create and start Flowrra app."""
    await app.start()
    yield app
    await app.stop()


@pytest.fixture
def adapter(app):
    """Create test adapter."""
    return DummyAdapter(app)


class TestBaseAdapterInit:
    """Test adapter initialization."""

    def test_adapter_creation(self, app):
        """Test creating an adapter."""
        adapter = DummyAdapter(app)
        assert adapter.flowrra is app
        assert adapter.manager is not None

    def test_adapter_has_manager(self, adapter):
        """Test adapter has FlowrraManager."""
        from flowrra.management import FlowrraManager

        assert isinstance(adapter.manager, FlowrraManager)
        assert adapter.manager.app is adapter.flowrra


class TestAbstractMethods:
    """Test abstract method enforcement."""

    def test_get_routes_must_be_implemented(self):
        """Test that get_routes must be implemented."""

        # Create adapter without implementing get_routes
        class IncompleteAdapter(BaseUIAdapter):
            pass

        # Should not be able to instantiate
        with pytest.raises(TypeError):
            IncompleteAdapter(None)

    def test_get_routes_returns_value(self, adapter):
        """Test get_routes returns a value."""
        routes = adapter.get_routes()
        assert routes is not None
        assert routes["type"] == "test_routes"


class TestSharedDataMethods:
    """Test shared data retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, running_app):
        """Test getting dashboard data."""
        adapter = DummyAdapter(running_app)
        data = await adapter.get_dashboard_data()

        # Check structure
        assert "stats" in data
        assert "recent_failed_tasks" in data
        assert "schedules" in data
        assert "total_schedules" in data

        # Check stats structure
        assert "app" in data["stats"]
        assert "executors" in data["stats"]
        assert "tasks" in data["stats"]

    @pytest.mark.asyncio
    async def test_get_tasks_page_data_no_filter(self, running_app):
        """Test getting tasks page data without filter."""
        adapter = DummyAdapter(running_app)
        data = await adapter.get_tasks_page_data()

        assert "registered_tasks" in data
        assert "tasks" in data
        assert "status_filter" in data
        assert data["status_filter"] is None

    @pytest.mark.asyncio
    async def test_get_tasks_page_data_with_filter(self, running_app):
        """Test getting tasks page data with status filter."""
        adapter = DummyAdapter(running_app)

        for status in ["pending", "running", "success", "failed"]:
            data = await adapter.get_tasks_page_data(status=status)
            assert data["status_filter"] == status
            assert "tasks" in data

    @pytest.mark.asyncio
    async def test_get_schedules_page_data(self, running_app):
        """Test getting schedules page data."""
        adapter = DummyAdapter(running_app)
        data = await adapter.get_schedules_page_data()

        assert "schedules" in data
        assert "scheduler_stats" in data
        assert "enabled_only" in data
        assert data["enabled_only"] is False

    @pytest.mark.asyncio
    async def test_get_schedules_page_data_enabled_only(self, running_app):
        """Test getting schedules with enabled_only filter."""
        adapter = DummyAdapter(running_app)
        data = await adapter.get_schedules_page_data(enabled_only=True)

        assert data["enabled_only"] is True


class TestFilePaths:
    """Test file path properties."""

    def test_templates_dir_exists(self, adapter):
        """Test templates_dir property."""
        templates_dir = adapter.templates_dir
        assert isinstance(templates_dir, Path)
        assert "templates" in str(templates_dir)

    def test_static_dir_exists(self, adapter):
        """Test static_dir property."""
        static_dir = adapter.static_dir
        assert isinstance(static_dir, Path)
        assert "static" in str(static_dir)


class TestUtilityMethods:
    """Test utility helper methods."""

    def test_format_datetime_none(self, adapter):
        """Test formatting None datetime."""
        result = adapter.format_datetime(None)
        assert result == "Never"

    def test_format_datetime_string(self, adapter):
        """Test formatting string datetime."""
        result = adapter.format_datetime("2024-01-01 10:00:00")
        assert result == "2024-01-01 10:00:00"

    def test_format_datetime_object(self, adapter):
        """Test formatting datetime object."""
        from datetime import datetime

        dt = datetime(2024, 1, 1, 10, 30, 45)
        result = adapter.format_datetime(dt)
        assert result == "2024-01-01 10:30:45"

    def test_format_duration_seconds(self, adapter):
        """Test formatting duration in seconds."""
        assert adapter.format_duration(45.5) == "45.5s"

    def test_format_duration_minutes(self, adapter):
        """Test formatting duration in minutes."""
        result = adapter.format_duration(150)  # 2.5 minutes
        assert "2.5m" in result

    def test_format_duration_hours(self, adapter):
        """Test formatting duration in hours."""
        result = adapter.format_duration(7200)  # 2 hours
        assert "2.0h" in result

    def test_get_status_color_pending(self, adapter):
        """Test status color for pending."""
        assert adapter.get_status_color("pending") == "yellow"

    def test_get_status_color_running(self, adapter):
        """Test status color for running."""
        assert adapter.get_status_color("running") == "blue"

    def test_get_status_color_success(self, adapter):
        """Test status color for success."""
        assert adapter.get_status_color("success") == "green"

    def test_get_status_color_failed(self, adapter):
        """Test status color for failed."""
        assert adapter.get_status_color("failed") == "red"

    def test_get_status_color_unknown(self, adapter):
        """Test status color for unknown status."""
        assert adapter.get_status_color("unknown") == "gray"


class TestAPIEndpoints:
    """Test standard API endpoint methods."""

    @pytest.mark.asyncio
    async def test_api_get_stats(self, running_app):
        """Test API stats endpoint."""
        adapter = DummyAdapter(running_app)
        stats = await adapter.get_stats()

        assert "app" in stats
        assert "executors" in stats
        assert "tasks" in stats

    @pytest.mark.asyncio
    async def test_api_health_check(self, running_app):
        """Test API health check endpoint."""
        adapter = DummyAdapter(running_app)
        health = await adapter.health_check()

        assert "healthy" in health
        assert "timestamp" in health
        assert "components" in health

    @pytest.mark.asyncio
    async def test_api_list_tasks(self, running_app):
        """Test API list tasks endpoint."""
        adapter = DummyAdapter(running_app)
        tasks = await adapter.list_tasks()

        assert isinstance(tasks, list)
        assert len(tasks) > 0
        assert "name" in tasks[0]

    @pytest.mark.asyncio
    async def test_api_get_task_existing(self, running_app):
        """Test API get task endpoint with existing task."""
        adapter = DummyAdapter(running_app)
        task_info = await adapter.get_task("test_task")

        assert task_info is not None
        assert task_info["name"] == "test_task"

    @pytest.mark.asyncio
    async def test_api_get_task_nonexistent(self, running_app):
        """Test API get task endpoint with non-existent task."""
        adapter = DummyAdapter(running_app)
        task_info = await adapter.get_task("nonexistent")

        assert task_info is None

    @pytest.mark.asyncio
    async def test_api_list_schedules(self, running_app):
        """Test API list schedules endpoint."""
        adapter = DummyAdapter(running_app)
        schedules = await adapter.list_schedules()

        assert isinstance(schedules, list)

    @pytest.mark.asyncio
    async def test_api_list_schedules_enabled_only(self, running_app):
        """Test API list schedules with enabled_only filter."""
        adapter = DummyAdapter(running_app)
        schedules = await adapter.list_schedules(enabled_only=True)

        assert isinstance(schedules, list)


class TestIntegration:
    """Integration tests for base adapter."""

    @pytest.mark.asyncio
    async def test_full_adapter_lifecycle(self, app):
        """Test full adapter lifecycle."""
        # Create adapter
        adapter = DummyAdapter(app)

        # Start app
        await app.start()

        try:
            # Get dashboard data
            dashboard = await adapter.get_dashboard_data()
            assert dashboard["stats"]["app"]["running"] is True

            # Get tasks data
            tasks_data = await adapter.get_tasks_page_data()
            assert len(tasks_data["registered_tasks"]) > 0

            # Use API endpoints
            stats = await adapter.get_stats()
            assert stats["app"]["running"] is True

            health = await adapter.health_check()
            assert health["healthy"] is True

        finally:
            await app.stop()

    @pytest.mark.asyncio
    async def test_adapter_with_scheduler(self, running_app):
        """Test adapter with scheduler configured."""
        # Create scheduler
        scheduler = running_app.create_scheduler()

        # Create adapter
        adapter = DummyAdapter(running_app)

        # Get dashboard data (should include scheduler info)
        dashboard = await adapter.get_dashboard_data()
        assert "schedules" in dashboard

        # Get scheduler stats via API
        stats = await adapter.get_stats()
        # Scheduler might be None if not started, but should be in structure
        assert "scheduler" in stats
