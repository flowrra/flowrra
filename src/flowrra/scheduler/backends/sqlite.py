"""SQLite backend for scheduler storage."""

import aiosqlite
import json
from datetime import datetime
from typing import List

from flowrra.scheduler.backends.base import BaseSchedulerBackend
from flowrra.scheduler.models import ScheduledTask, ScheduleType


class SQLiteSchedulerBackend(BaseSchedulerBackend):
    """SQLite-based scheduler backend for local persistent storage.

    Features:
        - Local file-based storage
        - No external dependencies
        - Automatic schema creation
        - Transaction support
        - Good for single-instance deployments

    Args:
        database_path: Path to SQLite database file (defaults to ".flowrra_schedule.db")
    """

    def __init__(self, database_path: str = ".flowrra_schedule.db"):
        """Initialize SQLite backend.

        Args:
            database_path: Path to database file
        """
        self.database_path = database_path
        self._db: aiosqlite.Connection | None = None

    async def _ensure_connected(self) -> aiosqlite.Connection:
        """Ensure database connection and schema exist."""
        if self._db is None:
            self._db = await aiosqlite.connect(self.database_path)
            self._db.row_factory = aiosqlite.Row
            await self._create_schema()

        return self._db

    async def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        if self._db is None:
            return

        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                schedule TEXT NOT NULL,
                args TEXT NOT NULL,
                kwargs TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                last_run_at TEXT,
                next_run_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                description TEXT,
                max_retries INTEGER NOT NULL DEFAULT 3,
                retry_delay REAL NOT NULL DEFAULT 1.0,
                priority INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        # Create indexes for efficient queries
        await self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_enabled
            ON scheduled_tasks(enabled)
            """
        )

        await self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_next_run
            ON scheduled_tasks(next_run_at)
            """
        )

        # Index for idempotency checks (find_by_definition)
        await self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_definition
            ON scheduled_tasks(task_name, schedule_type, schedule)
            """
        )

        await self._db.commit()

    async def create(self, task: ScheduledTask) -> None:
        """Create a new scheduled task."""
        db = await self._ensure_connected()

        # Check if task already exists
        async with db.execute(
            "SELECT id FROM scheduled_tasks WHERE id = ?", (task.id,)
        ) as cursor:
            existing = await cursor.fetchone()
            if existing:
                raise ValueError(f"Scheduled task with ID '{task.id}' already exists")

        # Insert new task
        await db.execute(
            """
            INSERT INTO scheduled_tasks (
                id, task_name, schedule_type, schedule, args, kwargs,
                enabled, last_run_at, next_run_at, created_at, updated_at,
                description, max_retries, retry_delay, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.task_name,
                task.schedule_type.value,
                task.schedule,
                json.dumps(list(task.args)),
                json.dumps(task.kwargs),
                1 if task.enabled else 0,
                task.last_run_at.isoformat() if task.last_run_at else None,
                task.next_run_at.isoformat() if task.next_run_at else None,
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
                task.description,
                task.max_retries,
                task.retry_delay,
                task.priority,
            ),
        )

        await db.commit()

    async def update(self, task: ScheduledTask) -> None:
        """Update an existing scheduled task."""
        db = await self._ensure_connected()

        # Update timestamp
        task.updated_at = datetime.now()

        result = await db.execute(
            """
            UPDATE scheduled_tasks
            SET task_name = ?, schedule_type = ?, schedule = ?, args = ?, kwargs = ?,
                enabled = ?, last_run_at = ?, next_run_at = ?, updated_at = ?,
                description = ?, max_retries = ?, retry_delay = ?, priority = ?
            WHERE id = ?
            """,
            (
                task.task_name,
                task.schedule_type.value,
                task.schedule,
                json.dumps(list(task.args)),
                json.dumps(task.kwargs),
                1 if task.enabled else 0,
                task.last_run_at.isoformat() if task.last_run_at else None,
                task.next_run_at.isoformat() if task.next_run_at else None,
                task.updated_at.isoformat(),
                task.description,
                task.max_retries,
                task.retry_delay,
                task.priority,
                task.id,
            ),
        )

        if result.rowcount == 0:
            raise ValueError(f"Scheduled task with ID '{task.id}' not found")

        await db.commit()

    async def delete(self, task_id: str) -> bool:
        """Delete a scheduled task."""
        db = await self._ensure_connected()

        result = await db.execute(
            "DELETE FROM scheduled_tasks WHERE id = ?", (task_id,)
        )

        await db.commit()

        return result.rowcount > 0

    async def get(self, task_id: str) -> ScheduledTask | None:
        """Get a scheduled task by ID."""
        db = await self._ensure_connected()

        async with db.execute(
            "SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None

            return self._row_to_task(row)

    async def list_all(self) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        db = await self._ensure_connected()

        async with db.execute("SELECT * FROM scheduled_tasks ORDER BY created_at") as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    async def list_enabled(self) -> List[ScheduledTask]:
        """List only enabled scheduled tasks."""
        db = await self._ensure_connected()

        async with db.execute(
            "SELECT * FROM scheduled_tasks WHERE enabled = 1 ORDER BY next_run_at"
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    async def list_due(self, now: datetime | None = None) -> List[ScheduledTask]:
        """List tasks that are due for execution."""
        if now is None:
            now = datetime.now()

        db = await self._ensure_connected()

        async with db.execute(
            """
            SELECT * FROM scheduled_tasks
            WHERE enabled = 1 AND next_run_at <= ?
            ORDER BY priority DESC, next_run_at
            """,
            (now.isoformat(),),
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    async def update_run_times(
        self, task_id: str, last_run: datetime, next_run: datetime
    ) -> None:
        """Update task run times after execution."""
        db = await self._ensure_connected()

        result = await db.execute(
            """
            UPDATE scheduled_tasks
            SET last_run_at = ?, next_run_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (last_run.isoformat(), next_run.isoformat(), datetime.now().isoformat(), task_id),
        )

        if result.rowcount == 0:
            raise ValueError(f"Scheduled task with ID '{task_id}' not found")

        await db.commit()

    async def clear(self) -> int:
        """Clear all scheduled tasks."""
        db = await self._ensure_connected()

        result = await db.execute("DELETE FROM scheduled_tasks")
        await db.commit()

        return result.rowcount

    async def find_by_definition(
        self,
        task_name: str,
        schedule_type: ScheduleType,
        schedule: str,
        args: tuple = (),
        kwargs: dict | None = None,
    ) -> ScheduledTask | None:
        """Find exact schedule match by complete definition.

        Used for idempotency - finds schedules with identical parameters.

        Args:
            task_name: Task name to match
            schedule_type: Type of schedule (CRON, INTERVAL, ONE_TIME)
            schedule: Schedule expression/value
            args: Task arguments tuple
            kwargs: Task keyword arguments dict

        Returns:
            Matching ScheduledTask if found, None otherwise
        """
        db = await self._ensure_connected()

        # Normalize kwargs
        normalized_kwargs = kwargs or {}

        # Serialize args and kwargs for comparison
        args_json = json.dumps(list(args))
        kwargs_json = json.dumps(normalized_kwargs)

        async with db.execute(
            """
            SELECT * FROM scheduled_tasks
            WHERE task_name = ?
              AND schedule_type = ?
              AND schedule = ?
              AND args = ?
              AND kwargs = ?
            LIMIT 1
            """,
            (task_name, schedule_type.value, schedule, args_json, kwargs_json),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None

            return self._row_to_task(row)

    async def close(self) -> None:
        """Close database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

    def _row_to_task(self, row: aiosqlite.Row) -> ScheduledTask:
        """Convert database row to ScheduledTask."""
        from flowrra.scheduler.models import ScheduleType

        return ScheduledTask(
            id=row["id"],
            task_name=row["task_name"],
            schedule_type=ScheduleType(row["schedule_type"]),
            schedule=row["schedule"],
            args=tuple(json.loads(row["args"])),
            kwargs=json.loads(row["kwargs"]),
            enabled=bool(row["enabled"]),
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
            next_run_at=datetime.fromisoformat(row["next_run_at"]) if row["next_run_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            description=row["description"],
            max_retries=row["max_retries"],
            retry_delay=row["retry_delay"],
            priority=row["priority"],
        )
