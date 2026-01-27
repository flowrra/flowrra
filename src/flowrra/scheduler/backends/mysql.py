"""MySQL backend for scheduler storage.

This backend uses aiomysql for async MySQL access,
ideal for distributed/production deployments.
"""

import json
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from flowrra.scheduler.backends.base import BaseSchedulerBackend
from flowrra.scheduler.models import ScheduledTask, ScheduleType


class MySQLSchedulerBackend(BaseSchedulerBackend):
    """MySQL-based scheduler backend.

    Features:
        - High-performance async operations via aiomysql
        - Connection pooling
        - Transaction support
        - JSON column support
        - Good for distributed/production deployments
        - Compatible with MariaDB

    Args:
        url: MySQL connection URL
            Format: mysql://user:pass@host:port/dbname
    """

    def __init__(self, url: str):
        """Initialize MySQL backend.

        Args:
            url: MySQL connection URL

        Raises:
            ImportError: If aiomysql is not installed
        """
        self.url = url
        self._pool = None

    async def _ensure_connected(self):
        """Ensure database connection pool exists."""
        if self._pool is None:
            try:
                import aiomysql
            except ImportError as e:
                raise ImportError(
                    "MySQL backend requires aiomysql package. "
                    "Install with: pip install flowrra[mysql]"
                ) from e

            parsed = urlparse(self.url)
            self._pool = await aiomysql.create_pool(
                host=parsed.hostname or "localhost",
                port=parsed.port or 3306,
                user=parsed.username or "root",
                password=parsed.password or "",
                db=parsed.path.lstrip("/") if parsed.path else "flowrra",
                autocommit=False,
            )

            await self._create_schema()

        return self._pool

    async def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        pool = self._pool

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scheduled_tasks (
                        id VARCHAR(255) PRIMARY KEY,
                        task_name VARCHAR(255) NOT NULL,
                        schedule_type VARCHAR(50) NOT NULL,
                        schedule TEXT NOT NULL,
                        args JSON NOT NULL,
                        kwargs JSON NOT NULL,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        last_run_at DATETIME,
                        next_run_at DATETIME,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        description TEXT,
                        max_retries INT NOT NULL DEFAULT 3,
                        retry_delay FLOAT NOT NULL DEFAULT 1.0,
                        priority INT NOT NULL DEFAULT 0,
                        INDEX idx_enabled (enabled),
                        INDEX idx_next_run (next_run_at),
                        INDEX idx_task_definition (task_name, schedule_type, schedule(255))
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
            await conn.commit()

    async def create(self, task: ScheduledTask) -> None:
        """Create a new scheduled task."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Check if exists
                await cursor.execute(
                    "SELECT 1 FROM scheduled_tasks WHERE id = %s", (task.id,)
                )
                exists = await cursor.fetchone()
                if exists:
                    raise ValueError(f"Scheduled task with ID '{task.id}' already exists")

                await cursor.execute(
                    """
                    INSERT INTO scheduled_tasks (
                        id, task_name, schedule_type, schedule, args, kwargs,
                        enabled, last_run_at, next_run_at, created_at, updated_at,
                        description, max_retries, retry_delay, priority
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        task.id,
                        task.task_name,
                        task.schedule_type.value,
                        task.schedule,
                        json.dumps(list(task.args)),
                        json.dumps(task.kwargs),
                        task.enabled,
                        task.last_run_at,
                        task.next_run_at,
                        task.created_at,
                        task.updated_at,
                        task.description,
                        task.max_retries,
                        task.retry_delay,
                        task.priority,
                    ),
                )
            await conn.commit()

    async def update(self, task: ScheduledTask) -> None:
        """Update an existing scheduled task."""
        pool = await self._ensure_connected()
        task.updated_at = datetime.now()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE scheduled_tasks
                    SET task_name = %s, schedule_type = %s, schedule = %s, args = %s, kwargs = %s,
                        enabled = %s, last_run_at = %s, next_run_at = %s, updated_at = %s,
                        description = %s, max_retries = %s, retry_delay = %s, priority = %s
                    WHERE id = %s
                    """,
                    (
                        task.task_name,
                        task.schedule_type.value,
                        task.schedule,
                        json.dumps(list(task.args)),
                        json.dumps(task.kwargs),
                        task.enabled,
                        task.last_run_at,
                        task.next_run_at,
                        task.updated_at,
                        task.description,
                        task.max_retries,
                        task.retry_delay,
                        task.priority,
                        task.id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ValueError(f"Scheduled task with ID '{task.id}' not found")
            await conn.commit()

    async def delete(self, task_id: str) -> bool:
        """Delete a scheduled task."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM scheduled_tasks WHERE id = %s", (task_id,)
                )
                deleted = cursor.rowcount > 0
            await conn.commit()
            return deleted

    async def get(self, task_id: str) -> ScheduledTask | None:
        """Get a scheduled task by ID."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM scheduled_tasks WHERE id = %s", (task_id,)
                )
                row = await cursor.fetchone()
                if row is None:
                    return None

                # Get column names
                columns = [desc[0] for desc in cursor.description]
                return self._row_to_task(dict(zip(columns, row)))

    async def list_all(self) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM scheduled_tasks ORDER BY created_at")
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [self._row_to_task(dict(zip(columns, row))) for row in rows]

    async def list_enabled(self) -> List[ScheduledTask]:
        """List only enabled scheduled tasks."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM scheduled_tasks WHERE enabled = TRUE ORDER BY next_run_at"
                )
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [self._row_to_task(dict(zip(columns, row))) for row in rows]

    async def list_due(self, now: datetime | None = None) -> List[ScheduledTask]:
        """List tasks that are due for execution."""
        if now is None:
            now = datetime.now()

        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT * FROM scheduled_tasks
                    WHERE enabled = TRUE AND next_run_at <= %s
                    ORDER BY priority DESC, next_run_at
                    """,
                    (now,),
                )
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [self._row_to_task(dict(zip(columns, row))) for row in rows]

    async def update_run_times(
        self, task_id: str, last_run: datetime, next_run: datetime
    ) -> None:
        """Update task run times after execution."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE scheduled_tasks
                    SET last_run_at = %s, next_run_at = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (last_run, next_run, datetime.now(), task_id),
                )

                if cursor.rowcount == 0:
                    raise ValueError(f"Scheduled task with ID '{task_id}' not found")
            await conn.commit()

    async def clear(self) -> int:
        """Clear all scheduled tasks."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM scheduled_tasks")
                count = cursor.rowcount
            await conn.commit()
            return count

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
        pool = await self._ensure_connected()

        # Normalize kwargs
        normalized_kwargs = kwargs or {}

        # Serialize args and kwargs for comparison
        args_json = json.dumps(list(args))
        kwargs_json = json.dumps(normalized_kwargs)

        import aiomysql

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT * FROM scheduled_tasks
                    WHERE task_name = %s
                      AND schedule_type = %s
                      AND schedule = %s
                      AND args = %s
                      AND kwargs = %s
                    LIMIT 1
                    """,
                    (task_name, schedule_type.value, schedule, args_json, kwargs_json),
                )
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_task(row)

    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    def _row_to_task(self, row: dict) -> ScheduledTask:
        """Convert MySQL row dict to ScheduledTask."""
        return ScheduledTask(
            id=row["id"],
            task_name=row["task_name"],
            schedule_type=ScheduleType(row["schedule_type"]),
            schedule=row["schedule"],
            args=tuple(json.loads(row["args"])),
            kwargs=json.loads(row["kwargs"]),
            enabled=bool(row["enabled"]),
            last_run_at=row["last_run_at"],
            next_run_at=row["next_run_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            description=row["description"],
            max_retries=row["max_retries"],
            retry_delay=row["retry_delay"],
            priority=row["priority"],
        )
