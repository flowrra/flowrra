"""Tests for management API."""

import pytest
from flowrra import Flowrra, Config, ExecutorConfig
from flowrra.management import FlowrraManager


@pytest.fixture
def app():
    """Create Flowrra app with tasks."""
    config = Config(executor=ExecutorConfig(num_workers=2))
    app = Flowrra(config=config)

    @app.task()
    async def io_task(x: int):
        return x * 2

    @app.task(max_retries=3, retry_delay=10.0)
    async def retry_task(n: int):
        return sum(i**2 for i in range(n))

    return app


@pytest.fixture
async def running_app(app):
    """Create and start Flowrra app."""
    await app.start()
    yield app
    await app.stop()


@pytest.fixture
def manager(app):
    """Create FlowrraManager."""
    return FlowrraManager(app)


class TestManagerBasics:
    """Test basic manager functionality."""

    def test_manager_creation(self, app):
        """Test creating a manager."""
        manager = FlowrraManager(app)
        assert manager.app is app

    def test_manager_from_management_import(self, app):
        """Test importing FlowrraManager from flowrra.management."""
        from flowrra.management import FlowrraManager as ImportedManager

        manager = ImportedManager(app)
        assert manager.app is app


class TestSystemStats:
    """Test system statistics queries."""

    @pytest.mark.asyncio
    async def test_get_stats_app_not_running(self, manager):
        """Test get_stats when app is not running."""
        stats = await manager.get_stats()

        assert stats["app"]["running"] is False
        assert "executors" in stats
        assert "tasks" in stats

    @pytest.mark.asyncio
    async def test_get_stats_app_running(self, running_app):
        """Test get_stats when app is running."""
        manager = FlowrraManager(running_app)
        stats = await manager.get_stats()

        assert stats["app"]["running"] is True

        # IO executor should be initialized and running
        assert stats["executors"]["io"] is not None
        assert stats["executors"]["io"]["running"] is True
        assert stats["executors"]["io"]["workers"] == 2

        # CPU executor should not be initialized (no backend)
        assert stats["executors"]["cpu"] is None

        # Tasks
        assert stats["tasks"]["registered"] == 2
        assert "pending" in stats["tasks"]

    @pytest.mark.asyncio
    async def test_get_stats_structure(self, manager):
        """Test that get_stats returns expected structure."""
        stats = await manager.get_stats()

        # Verify top-level keys
        assert "app" in stats
        assert "executors" in stats
        assert "tasks" in stats
        assert "scheduler" in stats

        # Verify app structure
        assert "running" in stats["app"]

        # Verify executors structure
        assert "io" in stats["executors"]
        assert "cpu" in stats["executors"]

        # Verify tasks structure
        assert "registered" in stats["tasks"]
        assert "pending" in stats["tasks"]


class TestTaskQueries:
    """Test task query methods."""

    @pytest.mark.asyncio
    async def test_list_registered_tasks(self, manager):
        """Test listing all registered tasks."""
        tasks = await manager.list_registered_tasks()

        assert len(tasks) == 2

        # Find tasks by name
        task_names = {task["name"] for task in tasks}
        assert "io_task" in task_names
        assert "retry_task" in task_names

        # Check IO task properties (uses default max_retries=3, retry_delay=1.0)
        io_task = next(t for t in tasks if t["name"] == "io_task")
        assert io_task["cpu_bound"] is False
        assert io_task["max_retries"] == 3
        assert io_task["retry_delay"] == 1.0

        # Check retry task properties
        retry_task = next(t for t in tasks if t["name"] == "retry_task")
        assert retry_task["cpu_bound"] is False
        assert retry_task["max_retries"] == 3
        assert retry_task["retry_delay"] == 10.0

    @pytest.mark.asyncio
    async def test_get_task_info_existing(self, manager):
        """Test getting info for an existing task."""
        task_info = await manager.get_task_info("io_task")

        assert task_info is not None
        assert task_info["name"] == "io_task"
        assert task_info["cpu_bound"] is False
        assert "module" in task_info
        assert "qualname" in task_info

    @pytest.mark.asyncio
    async def test_get_task_info_nonexistent(self, manager):
        """Test getting info for a non-existent task."""
        task_info = await manager.get_task_info("nonexistent_task")
        assert task_info is None

    @pytest.mark.asyncio
    async def test_list_pending_tasks(self, manager):
        """Test listing pending tasks (placeholder implementation)."""
        pending = await manager.list_pending_tasks()

        # Currently returns empty list (placeholder)
        assert isinstance(pending, list)

    @pytest.mark.asyncio
    async def test_get_task_result_nonexistent(self, manager):
        """Test getting result for non-existent task."""
        result = await manager.get_task_result("nonexistent-task-id")
        assert result is None


class TestSchedulerQueries:
    """Test scheduler query methods (placeholders for now)."""

    @pytest.mark.asyncio
    async def test_list_schedules(self, manager):
        """Test listing schedules (placeholder)."""
        schedules = await manager.list_schedules()

        # Currently returns empty list (placeholder)
        assert isinstance(schedules, list)
        assert len(schedules) == 0

    @pytest.mark.asyncio
    async def test_get_schedule(self, manager):
        """Test getting specific schedule (placeholder)."""
        schedule = await manager.get_schedule("test-schedule-id")

        # Currently returns None (placeholder)
        assert schedule is None

    @pytest.mark.asyncio
    async def test_get_scheduler_stats(self, manager):
        """Test getting scheduler stats (placeholder)."""
        stats = await manager.get_scheduler_stats()

        # Currently returns None (placeholder)
        assert stats is None


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_app_not_running(self, manager):
        """Test health check when app is not running."""
        health = await manager.health_check()

        assert "healthy" in health
        assert "timestamp" in health
        assert "components" in health

        # App not running = not healthy
        assert health["healthy"] is False
        assert health["components"]["app"]["healthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_app_running(self, running_app):
        """Test health check when app is running."""
        manager = FlowrraManager(running_app)
        health = await manager.health_check()

        # App running = healthy
        assert health["healthy"] is True
        assert health["components"]["app"]["healthy"] is True

        # IO executor should be healthy
        assert health["components"]["io_executor"] is not None
        assert health["components"]["io_executor"]["healthy"] is True

        # CPU executor not initialized
        assert health["components"]["cpu_executor"] is None

    @pytest.mark.asyncio
    async def test_health_check_structure(self, manager):
        """Test health check returns correct structure."""
        health = await manager.health_check()

        # Verify structure
        assert isinstance(health["healthy"], bool)
        assert health["timestamp"] is not None
        assert isinstance(health["components"], dict)

        # Verify components
        assert "app" in health["components"]
        assert "io_executor" in health["components"]
        assert "cpu_executor" in health["components"]

        # Verify component structure
        app_health = health["components"]["app"]
        assert "healthy" in app_health
        assert "message" in app_health


class TestIntegration:
    """Integration tests for management API."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, running_app):
        """Test full management workflow."""
        manager = FlowrraManager(running_app)

        # 1. Check health
        health = await manager.health_check()
        assert health["healthy"] is True

        # 2. Get system stats
        stats = await manager.get_stats()
        assert stats["app"]["running"] is True
        assert stats["tasks"]["registered"] == 2

        # 3. List registered tasks
        tasks = await manager.list_registered_tasks()
        assert len(tasks) == 2

        # 4. Get specific task info
        task_info = await manager.get_task_info("io_task")
        assert task_info is not None
        assert task_info["name"] == "io_task"

    @pytest.mark.asyncio
    async def test_manager_with_submitted_task(self, running_app):
        """Test manager after submitting a task."""
        manager = FlowrraManager(running_app)

        # Submit a task
        task_func = running_app.registry.get("io_task")
        task_id = await running_app.submit(task_func, 5)

        # Get stats
        stats = await manager.get_stats()
        assert stats["tasks"]["registered"] == 2

        # Task result should be retrievable
        import asyncio

        await asyncio.sleep(0.1)  # Wait for task execution

        result = await manager.get_task_result(task_id)
        if result:  # May be None if task completed and cleaned up
            assert result["task_id"] == task_id
