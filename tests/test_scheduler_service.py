"""Tests for scheduler service."""

import pytest
import asyncio
from datetime import datetime, timedelta
from flowrra.scheduler import Scheduler, ScheduledTask, ScheduleType
from flowrra.scheduler.backends.sqlite import SQLiteSchedulerBackend
from flowrra.registry import TaskRegistry


@pytest.fixture
async def scheduler_backend():
    """Create in-memory SQLite backend."""
    backend = SQLiteSchedulerBackend(database_path=":memory:")
    yield backend
    await backend.close()


@pytest.fixture
def task_registry():
    """Create task registry with sample tasks."""
    registry = TaskRegistry()

    @registry.task()
    async def test_task(x: int):
        return x * 2

    @registry.task()
    async def another_task():
        return "done"

    return registry


@pytest.fixture
async def io_executor(task_registry):
    """Create IOExecutor."""
    from flowrra import Config, ExecutorConfig, IOExecutor

    config = Config(executor=ExecutorConfig(num_workers=2))
    executor = IOExecutor(config=config)
    await executor.start()
    yield executor
    await executor.stop()


@pytest.fixture
async def scheduler(scheduler_backend, task_registry, io_executor):
    """Create scheduler instance with executor integration."""
    scheduler = Scheduler(
        backend=scheduler_backend,
        registry=task_registry,
        check_interval=0.1,  # Fast checking for tests
        io_executor=io_executor
    )
    yield scheduler
    await scheduler.stop()


class TestSchedulerBasics:
    """Test basic scheduler functionality."""

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test starting and stopping scheduler."""
        assert scheduler.is_running is False

        await scheduler.start()
        assert scheduler.is_running is True

        await scheduler.stop()
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_schedule_cron_task(self, scheduler):
        """Test scheduling a task with cron expression."""
        task_id = await scheduler.schedule_cron(
            task_name="test_task",
            cron="0 9 * * *",
            args=(5,),
            description="Daily task at 9 AM"
        )

        assert task_id is not None

        # Verify task was created
        task = await scheduler.get_scheduled_task(task_id)
        assert task is not None
        assert task.task_name == "test_task"
        assert task.schedule == "0 9 * * *"
        assert task.schedule_type == ScheduleType.CRON

    @pytest.mark.asyncio
    async def test_schedule_interval_task(self, scheduler):
        """Test scheduling a task with interval."""
        task_id = await scheduler.schedule_interval(
            task_name="test_task",
            interval=300,  # 5 minutes
            args=(10,),
            description="Every 5 minutes"
        )

        task = await scheduler.get_scheduled_task(task_id)
        assert task is not None
        assert task.schedule_type == ScheduleType.INTERVAL
        assert task.schedule == "300"

    @pytest.mark.asyncio
    async def test_schedule_once_task(self, scheduler):
        """Test scheduling a one-time task."""
        run_at = datetime.now() + timedelta(hours=1)

        task_id = await scheduler.schedule_once(
            task_name="test_task",
            run_at=run_at,
            args=(20,),
            description="One-time task"
        )

        task = await scheduler.get_scheduled_task(task_id)
        assert task is not None
        assert task.schedule_type == ScheduleType.ONE_TIME
        assert task.next_run_at is not None

    @pytest.mark.asyncio
    async def test_schedule_unregistered_task_fails(self, scheduler):
        """Test that scheduling unregistered task fails."""
        with pytest.raises(ValueError, match="not registered"):
            await scheduler.schedule_cron(
                task_name="nonexistent_task",
                cron="0 9 * * *"
            )

    @pytest.mark.asyncio
    async def test_schedule_invalid_cron_fails(self, scheduler):
        """Test that invalid cron expression fails."""
        with pytest.raises(ValueError):
            await scheduler.schedule_cron(
                task_name="test_task",
                cron="invalid cron"
            )

    @pytest.mark.asyncio
    async def test_schedule_invalid_interval_fails(self, scheduler):
        """Test that invalid interval fails."""
        with pytest.raises(ValueError, match="must be positive"):
            await scheduler.schedule_interval(
                task_name="test_task",
                interval=-5
            )


class TestSchedulerManagement:
    """Test scheduler task management."""

    @pytest.mark.asyncio
    async def test_unschedule_task(self, scheduler):
        """Test unscheduling a task."""
        task_id = await scheduler.schedule_cron(
            task_name="test_task",
            cron="0 9 * * *"
        )

        deleted = await scheduler.unschedule(task_id)
        assert deleted is True

        task = await scheduler.get_scheduled_task(task_id)
        assert task is None

    @pytest.mark.asyncio
    async def test_enable_disable_task(self, scheduler):
        """Test enabling and disabling tasks."""
        task_id = await scheduler.schedule_cron(
            task_name="test_task",
            cron="0 9 * * *",
            enabled=True
        )

        # Disable task
        await scheduler.disable_task(task_id)
        task = await scheduler.get_scheduled_task(task_id)
        assert task.enabled is False

        # Enable task
        await scheduler.enable_task(task_id)
        task = await scheduler.get_scheduled_task(task_id)
        assert task.enabled is True

    @pytest.mark.asyncio
    async def test_list_scheduled_tasks(self, scheduler):
        """Test listing all scheduled tasks."""
        # Schedule multiple tasks
        await scheduler.schedule_cron(task_name="test_task", cron="0 9 * * *")
        await scheduler.schedule_interval(task_name="another_task", interval=300)

        tasks = await scheduler.list_scheduled_tasks()
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_custom_task_id(self, scheduler):
        """Test scheduling with custom task ID."""
        custom_id = "my-custom-id"

        task_id = await scheduler.schedule_cron(
            task_name="test_task",
            cron="0 9 * * *",
            task_id=custom_id
        )

        assert task_id == custom_id

        task = await scheduler.get_scheduled_task(custom_id)
        assert task is not None


class TestSchedulerExecution:
    """Test scheduler task execution."""

    @pytest.mark.asyncio
    async def test_execute_due_task(self, scheduler):
        """Test that scheduler executes due tasks."""
        executed_tasks = []

        # Set up callback to track execution
        async def submit_callback(task_func, *args, **kwargs):
            executed_tasks.append((task_func.task_name, args, kwargs))

        scheduler.set_submit_callback(submit_callback)

        # Schedule task in the past (due now)
        past_time = datetime.now() - timedelta(minutes=5)
        await scheduler.backend.create(
            ScheduledTask(
                id="test-due-task",
                task_name="test_task",
                schedule_type=ScheduleType.CRON,
                schedule="0 9 * * *",
                args=(42,),
                kwargs={"foo": "bar"},
                enabled=True,
                next_run_at=past_time,
            )
        )

        # Start scheduler and wait for execution
        await scheduler.start()
        await asyncio.sleep(0.3)  # Wait for scheduler to check

        # Verify task was executed
        assert len(executed_tasks) == 1
        assert executed_tasks[0][0] == "test_task"
        assert executed_tasks[0][1] == (42,)
        assert executed_tasks[0][2] == {"foo": "bar"}

    @pytest.mark.asyncio
    async def test_next_run_calculation_cron(self, scheduler):
        """Test next run calculation for cron tasks."""
        now = datetime.now()
        past_time = now - timedelta(minutes=5)

        await scheduler.backend.create(
            ScheduledTask(
                id="cron-task",
                task_name="test_task",
                schedule_type=ScheduleType.CRON,
                schedule="*/5 * * * *",  # Every 5 minutes
                enabled=True,
                next_run_at=past_time,
            )
        )

        # Set dummy callback
        async def dummy_callback(task_func, *args, **kwargs):
            pass

        scheduler.set_submit_callback(dummy_callback)

        await scheduler.start()
        await asyncio.sleep(0.3)

        # Check that next_run_at was updated
        task = await scheduler.get_scheduled_task("cron-task")
        assert task.next_run_at > now

    @pytest.mark.asyncio
    async def test_next_run_calculation_interval(self, scheduler):
        """Test next run calculation for interval tasks."""
        now = datetime.now()
        past_time = now - timedelta(seconds=5)

        await scheduler.backend.create(
            ScheduledTask(
                id="interval-task",
                task_name="test_task",
                schedule_type=ScheduleType.INTERVAL,
                schedule="10",  # 10 seconds
                enabled=True,
                next_run_at=past_time,
            )
        )

        async def dummy_callback(task_func, *args, **kwargs):
            pass

        scheduler.set_submit_callback(dummy_callback)

        await scheduler.start()
        await asyncio.sleep(0.3)

        task = await scheduler.get_scheduled_task("interval-task")
        # Next run should be approximately 10 seconds from execution
        assert task.next_run_at > now

    @pytest.mark.asyncio
    async def test_one_time_task_disabled_after_execution(self, scheduler):
        """Test that one-time tasks are disabled after execution."""
        past_time = datetime.now() - timedelta(minutes=5)

        await scheduler.backend.create(
            ScheduledTask(
                id="one-time-task",
                task_name="test_task",
                schedule_type=ScheduleType.ONE_TIME,
                schedule=past_time.isoformat(),
                enabled=True,
                next_run_at=past_time,
            )
        )

        async def dummy_callback(task_func, *args, **kwargs):
            pass

        scheduler.set_submit_callback(dummy_callback)

        await scheduler.start()
        await asyncio.sleep(0.3)

        task = await scheduler.get_scheduled_task("one-time-task")
        assert task.enabled is False

    @pytest.mark.asyncio
    async def test_disabled_tasks_not_executed(self, scheduler):
        """Test that disabled tasks are not executed."""
        executed_tasks = []

        async def submit_callback(task_func, *args, **kwargs):
            executed_tasks.append(task_func.task_name)

        scheduler.set_submit_callback(submit_callback)

        # Schedule disabled task in the past
        past_time = datetime.now() - timedelta(minutes=5)
        await scheduler.backend.create(
            ScheduledTask(
                id="disabled-task",
                task_name="test_task",
                schedule_type=ScheduleType.CRON,
                schedule="0 9 * * *",
                enabled=False,  # Disabled
                next_run_at=past_time,
            )
        )

        await scheduler.start()
        await asyncio.sleep(0.3)

        # Verify task was NOT executed
        assert len(executed_tasks) == 0


class TestSchedulerConfiguration:
    """Test scheduler configuration."""

    @pytest.mark.asyncio
    async def test_custom_check_interval(self, scheduler_backend, task_registry):
        """Test scheduler with custom check interval."""
        scheduler = Scheduler(
            backend=scheduler_backend,
            registry=task_registry,
            check_interval=5.0
        )

        assert scheduler.check_interval == 5.0

        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_scheduler_priority_ordering(self, scheduler):
        """Test that high priority tasks are listed first."""
        now = datetime.now()
        past = now - timedelta(minutes=5)

        # Create tasks with different priorities
        await scheduler.backend.create(
            ScheduledTask(
                id="low-priority",
                task_name="test_task",
                schedule_type=ScheduleType.CRON,
                schedule="0 9 * * *",
                enabled=True,
                next_run_at=past,
                priority=1,
            )
        )

        await scheduler.backend.create(
            ScheduledTask(
                id="high-priority",
                task_name="test_task",
                schedule_type=ScheduleType.CRON,
                schedule="0 9 * * *",
                enabled=True,
                next_run_at=past,
                priority=10,
            )
        )

        due_tasks = await scheduler.backend.list_due(now)

        # High priority task should be first
        assert due_tasks[0].id == "high-priority"
        assert due_tasks[1].id == "low-priority"


class TestSchedulerIntegration:
    """Test scheduler integration features."""

    @pytest.mark.asyncio
    async def test_start_without_executors_or_callback_fails(self, scheduler_backend, task_registry):
        """Test that starting without executors or callback raises error."""
        scheduler = Scheduler(
            backend=scheduler_backend,
            registry=task_registry
        )

        with pytest.raises(ValueError, match="requires either"):
            await scheduler.start()

    @pytest.mark.asyncio
    async def test_callback_backward_compatibility(self, scheduler_backend, task_registry):
        """Test that callback pattern still works."""
        executed_tasks = []

        async def submit_callback(task_func, *args, **kwargs):
            executed_tasks.append((task_func.task_name, args, kwargs))

        scheduler = Scheduler(
            backend=scheduler_backend,
            registry=task_registry,
            check_interval=0.1
        )
        scheduler.set_submit_callback(submit_callback)

        # Schedule task in the past (due now)
        past_time = datetime.now() - timedelta(minutes=5)
        await scheduler.backend.create(
            ScheduledTask(
                id="callback-task",
                task_name="test_task",
                schedule_type=ScheduleType.CRON,
                schedule="0 9 * * *",
                args=(42,),
                kwargs={"foo": "bar"},
                enabled=True,
                next_run_at=past_time,
            )
        )

        # Start scheduler and wait for execution
        await scheduler.start()
        await asyncio.sleep(0.3)
        await scheduler.stop()

        # Verify callback was called
        assert len(executed_tasks) == 1
        assert executed_tasks[0][0] == "test_task"
        assert executed_tasks[0][1] == (42,)
        assert executed_tasks[0][2] == {"foo": "bar"}
