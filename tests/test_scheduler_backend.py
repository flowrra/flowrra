"""Tests for scheduler backends."""

import pytest
import asyncio
from datetime import datetime, timedelta
from flowrra.scheduler.models import ScheduledTask, ScheduleType
from flowrra.scheduler.backends.sqlite import SQLiteSchedulerBackend
from flowrra.scheduler.backends import get_scheduler_backend


@pytest.fixture
async def sqlite_backend():
    """Create SQLite backend for testing."""
    backend = SQLiteSchedulerBackend(database_path=":memory:")
    yield backend
    await backend.close()


@pytest.fixture
def sample_task():
    """Create a sample scheduled task."""
    return ScheduledTask(
        id="test-task-1",
        task_name="test_task",
        schedule_type=ScheduleType.CRON,
        schedule="0 9 * * *",
        args=(1, 2),
        kwargs={"foo": "bar"},
        enabled=True,
        next_run_at=datetime.now() + timedelta(hours=1),
        description="Test task",
    )


class TestSQLiteBackend:
    """Test SQLite scheduler backend."""

    @pytest.mark.asyncio
    async def test_create_task(self, sqlite_backend, sample_task):
        """Test creating a scheduled task."""
        await sqlite_backend.create(sample_task)

        retrieved = await sqlite_backend.get(sample_task.id)
        assert retrieved is not None
        assert retrieved.id == sample_task.id
        assert retrieved.task_name == sample_task.task_name
        assert retrieved.schedule == sample_task.schedule

    @pytest.mark.asyncio
    async def test_create_duplicate_fails(self, sqlite_backend, sample_task):
        """Test that creating duplicate task fails."""
        await sqlite_backend.create(sample_task)

        with pytest.raises(ValueError, match="already exists"):
            await sqlite_backend.create(sample_task)

    @pytest.mark.asyncio
    async def test_update_task(self, sqlite_backend, sample_task):
        """Test updating a scheduled task."""
        await sqlite_backend.create(sample_task)

        # Update task
        sample_task.schedule = "0 10 * * *"
        sample_task.enabled = False
        await sqlite_backend.update(sample_task)

        # Verify update
        retrieved = await sqlite_backend.get(sample_task.id)
        assert retrieved.schedule == "0 10 * * *"
        assert retrieved.enabled is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_fails(self, sqlite_backend, sample_task):
        """Test that updating nonexistent task fails."""
        with pytest.raises(ValueError, match="not found"):
            await sqlite_backend.update(sample_task)

    @pytest.mark.asyncio
    async def test_delete_task(self, sqlite_backend, sample_task):
        """Test deleting a scheduled task."""
        await sqlite_backend.create(sample_task)

        deleted = await sqlite_backend.delete(sample_task.id)
        assert deleted is True

        # Verify deletion
        retrieved = await sqlite_backend.get(sample_task.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, sqlite_backend):
        """Test deleting nonexistent task returns False."""
        deleted = await sqlite_backend.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_all(self, sqlite_backend):
        """Test listing all scheduled tasks."""
        tasks = [
            ScheduledTask(
                id=f"task-{i}",
                task_name=f"test_task_{i}",
                schedule_type=ScheduleType.CRON,
                schedule="0 9 * * *",
                next_run_at=datetime.now() + timedelta(hours=i),
            )
            for i in range(3)
        ]

        for task in tasks:
            await sqlite_backend.create(task)

        all_tasks = await sqlite_backend.list_all()
        assert len(all_tasks) == 3

    @pytest.mark.asyncio
    async def test_list_enabled(self, sqlite_backend):
        """Test listing only enabled tasks."""
        enabled_task = ScheduledTask(
            id="enabled",
            task_name="enabled_task",
            schedule_type=ScheduleType.CRON,
            schedule="0 9 * * *",
            enabled=True,
            next_run_at=datetime.now() + timedelta(hours=1),
        )

        disabled_task = ScheduledTask(
            id="disabled",
            task_name="disabled_task",
            schedule_type=ScheduleType.CRON,
            schedule="0 9 * * *",
            enabled=False,
            next_run_at=datetime.now() + timedelta(hours=1),
        )

        await sqlite_backend.create(enabled_task)
        await sqlite_backend.create(disabled_task)

        enabled_tasks = await sqlite_backend.list_enabled()
        assert len(enabled_tasks) == 1
        assert enabled_tasks[0].id == "enabled"

    @pytest.mark.asyncio
    async def test_list_due(self, sqlite_backend):
        """Test listing tasks due for execution."""
        now = datetime.now()

        # Past task (due)
        past_task = ScheduledTask(
            id="past",
            task_name="past_task",
            schedule_type=ScheduleType.CRON,
            schedule="0 9 * * *",
            enabled=True,
            next_run_at=now - timedelta(hours=1),
        )

        # Future task (not due)
        future_task = ScheduledTask(
            id="future",
            task_name="future_task",
            schedule_type=ScheduleType.CRON,
            schedule="0 9 * * *",
            enabled=True,
            next_run_at=now + timedelta(hours=1),
        )

        await sqlite_backend.create(past_task)
        await sqlite_backend.create(future_task)

        due_tasks = await sqlite_backend.list_due(now)
        assert len(due_tasks) == 1
        assert due_tasks[0].id == "past"

    @pytest.mark.asyncio
    async def test_update_run_times(self, sqlite_backend, sample_task):
        """Test updating task run times."""
        await sqlite_backend.create(sample_task)

        now = datetime.now()
        next_run = now + timedelta(hours=24)

        await sqlite_backend.update_run_times(sample_task.id, now, next_run)

        retrieved = await sqlite_backend.get(sample_task.id)
        assert retrieved.last_run_at is not None
        assert retrieved.next_run_at is not None
        # Allow small time difference due to serialization
        assert abs((retrieved.last_run_at - now).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_clear(self, sqlite_backend):
        """Test clearing all tasks."""
        tasks = [
            ScheduledTask(
                id=f"task-{i}",
                task_name=f"test_task_{i}",
                schedule_type=ScheduleType.CRON,
                schedule="0 9 * * *",
                next_run_at=datetime.now() + timedelta(hours=i),
            )
            for i in range(3)
        ]

        for task in tasks:
            await sqlite_backend.create(task)

        count = await sqlite_backend.clear()
        assert count == 3

        all_tasks = await sqlite_backend.list_all()
        assert len(all_tasks) == 0

    @pytest.mark.asyncio
    async def test_task_serialization(self, sqlite_backend):
        """Test that complex task data is properly serialized."""
        task = ScheduledTask(
            id="complex-task",
            task_name="complex",
            schedule_type=ScheduleType.INTERVAL,
            schedule="300",
            args=(1, "test", {"nested": "dict"}),
            kwargs={"key1": "value1", "key2": [1, 2, 3]},
            enabled=True,
            next_run_at=datetime.now(),
            priority=10,
            max_retries=5,
            retry_delay=2.5,
        )

        await sqlite_backend.create(task)
        retrieved = await sqlite_backend.get(task.id)

        assert retrieved.args == task.args
        assert retrieved.kwargs == task.kwargs
        assert retrieved.priority == task.priority
        assert retrieved.max_retries == task.max_retries
        assert retrieved.retry_delay == task.retry_delay


class TestBackendFactory:
    """Test scheduler backend factory."""

    def test_factory_default_sqlite(self):
        """Test factory returns SQLite backend by default."""
        backend = get_scheduler_backend()
        assert isinstance(backend, SQLiteSchedulerBackend)

    def test_factory_sqlite_with_path(self):
        """Test factory with SQLite path."""
        backend = get_scheduler_backend("sqlite:///custom.db")
        assert isinstance(backend, SQLiteSchedulerBackend)
        assert backend.database_path == "custom.db"

    def test_factory_unsupported_scheme(self):
        """Test factory with unsupported scheme."""
        with pytest.raises(ValueError, match="Unsupported scheduler backend"):
            get_scheduler_backend("mongodb://localhost/db")  # MongoDB is not supported

    @pytest.mark.skipif(
        not __import__('importlib').util.find_spec('asyncpg'),
        reason="PostgreSQL tests require asyncpg"
    )
    def test_factory_postgresql(self):
        """Test factory with PostgreSQL URL."""
        from flowrra.scheduler.backends.sql import SQLSchedulerBackend

        backend = get_scheduler_backend("postgresql://user:pass@localhost/flowrra")
        assert isinstance(backend, SQLSchedulerBackend)
        assert backend.db_type == "postgresql"

    @pytest.mark.skipif(
        not __import__('importlib').util.find_spec('aiomysql'),
        reason="MySQL tests require aiomysql"
    )
    def test_factory_mysql(self):
        """Test factory with MySQL URL."""
        from flowrra.scheduler.backends.sql import SQLSchedulerBackend

        backend = get_scheduler_backend("mysql://user:pass@localhost/flowrra")
        assert isinstance(backend, SQLSchedulerBackend)
        assert backend.db_type == "mysql"
