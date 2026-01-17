"""Persistent task scheduling for Flowrra.

This module provides Celery Beat-like scheduling capabilities with support
for cron expressions, intervals, and one-time task execution.

Example:
    from flowrra import Flowrra
    from flowrra.scheduler import Scheduler
    from flowrra.scheduler.backends import get_scheduler_backend

    # Create Flowrra app
    app = Flowrra.from_urls()

    # Create scheduler with SQLite backend (default)
    backend = get_scheduler_backend()
    scheduler = Scheduler(backend=backend, registry=app.registry)

    # Schedule a task with cron expression
    await scheduler.schedule_cron(
        task_name="my_task",
        cron="0 9 * * *",  # Daily at 9 AM
        args=(1, 2),
        kwargs={"foo": "bar"}
    )

    # Start scheduler
    await scheduler.start()
"""

from flowrra.scheduler.scheduler import Scheduler
from flowrra.scheduler.models import ScheduledTask, ScheduleType
from flowrra.scheduler.cron import CronExpression

__all__ = ["Scheduler", "ScheduledTask", "ScheduleType", "CronExpression"]
