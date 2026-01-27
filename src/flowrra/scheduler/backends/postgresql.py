"""PostgreSQL backend for scheduler storage.

This backend uses asyncpg for high-performance async PostgreSQL access,
ideal for distributed/production deployments.
"""

import json
from datetime import datetime
from typing import List

from flowrra.scheduler.backends.base import BaseSchedulerBackend
from flowrra.scheduler.models import ScheduledTask, ScheduleType


class PostgreSQLSchedulerBackend(BaseSchedulerBackend):
    """PostgreSQL-based scheduler backend.

    Features:
        - High-performance async operations via asyncpg
        - Connection pooling
        - Transaction support
        - JSONB for efficient JSON storage and queries
        - Good for distributed/production deployments

    Args:
        url: PostgreSQL connection URL
            Format: postgresql://user:pass@host:port/dbname
    """

    def __init__(self, url: str):
        """Initialize PostgreSQL backend.

        Args:
            url: PostgreSQL connection URL

        Raises:
            ImportError: If asyncpg is not installed
        """
        self.url = url
        self._pool = None

    async def _ensure_connected(self):
        """Ensure database connection pool exists."""
        if self._pool is None:
            try:
                import asyncpg
            except ImportError as e:
                raise ImportError(
                    "PostgreSQL backend requires asyncpg package. "
                    "Install with: pip install flowrra[postgresql]"
                ) from e

            self._pool = await asyncpg.create_pool(self.url)
            await self._create_schema()

        return self._pool

    async def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        pool = self._pool

        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    args JSONB NOT NULL,
                    kwargs JSONB NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    last_run_at TIMESTAMP,
                    next_run_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    description TEXT,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    retry_delay REAL NOT NULL DEFAULT 1.0,
                    priority INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_enabled ON scheduled_tasks(enabled)"
            )

            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_next_run ON scheduled_tasks(next_run_at)"
            )

            # Index for idempotency checks (find_by_definition)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_definition ON scheduled_tasks(task_name, schedule_type, schedule)"
            )

    async def create(self, task: ScheduledTask) -> None:
        """Create a new scheduled task."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            # Check if exists
            exists = await conn.fetchval(
                "SELECT 1 FROM scheduled_tasks WHERE id = $1", task.id
            )
            if exists:
                raise ValueError(f"Scheduled task with ID '{task.id}' already exists")

            await conn.execute(
                """
                INSERT INTO scheduled_tasks (
                    id, task_name, schedule_type, schedule, args, kwargs,
                    enabled, last_run_at, next_run_at, created_at, updated_at,
                    description, max_retries, retry_delay, priority
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                """,
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
            )

    async def update(self, task: ScheduledTask) -> None:
        """Update an existing scheduled task."""
        pool = await self._ensure_connected()
        task.updated_at = datetime.now()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE scheduled_tasks
                SET task_name = $1, schedule_type = $2, schedule = $3, args = $4, kwargs = $5,
                    enabled = $6, last_run_at = $7, next_run_at = $8, updated_at = $9,
                    description = $10, max_retries = $11, retry_delay = $12, priority = $13
                WHERE id = $14
                """,
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
            )

            if result == "UPDATE 0":
                raise ValueError(f"Scheduled task with ID '{task.id}' not found")

    async def delete(self, task_id: str) -> bool:
        """Delete a scheduled task."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM scheduled_tasks WHERE id = $1", task_id
            )
            return result != "DELETE 0"

    async def get(self, task_id: str) -> ScheduledTask | None:
        """Get a scheduled task by ID."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM scheduled_tasks WHERE id = $1", task_id
            )
            if row is None:
                return None
            return self._row_to_task(row)

    async def list_all(self) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM scheduled_tasks ORDER BY created_at")
            return [self._row_to_task(row) for row in rows]

    async def list_enabled(self) -> List[ScheduledTask]:
        """List only enabled scheduled tasks."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM scheduled_tasks WHERE enabled = TRUE ORDER BY next_run_at"
            )
            return [self._row_to_task(row) for row in rows]

    async def list_due(self, now: datetime | None = None) -> List[ScheduledTask]:
        """List tasks that are due for execution."""
        if now is None:
            now = datetime.now()

        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM scheduled_tasks
                WHERE enabled = TRUE AND next_run_at <= $1
                ORDER BY priority DESC, next_run_at
                """,
                now,
            )
            return [self._row_to_task(row) for row in rows]

    async def update_run_times(
        self, task_id: str, last_run: datetime, next_run: datetime
    ) -> None:
        """Update task run times after execution."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE scheduled_tasks
                SET last_run_at = $1, next_run_at = $2, updated_at = $3
                WHERE id = $4
                """,
                last_run,
                next_run,
                datetime.now(),
                task_id,
            )

            if result == "UPDATE 0":
                raise ValueError(f"Scheduled task with ID '{task_id}' not found")

    async def clear(self) -> int:
        """Clear all scheduled tasks."""
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM scheduled_tasks")
            # Parse "DELETE N" to get count
            return int(result.split()[1]) if result else 0

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

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM scheduled_tasks
                WHERE task_name = $1
                  AND schedule_type = $2
                  AND schedule = $3
                  AND args::text = $4::text
                  AND kwargs::text = $5::text
                LIMIT 1
                """,
                task_name,
                schedule_type.value,
                schedule,
                args_json,
                kwargs_json,
            )
            if row is None:
                return None
            return self._row_to_task(row)

    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _row_to_task(self, row) -> ScheduledTask:
        """Convert PostgreSQL row to ScheduledTask."""
        return ScheduledTask(
            id=row["id"],
            task_name=row["task_name"],
            schedule_type=ScheduleType(row["schedule_type"]),
            schedule=row["schedule"],
            args=tuple(json.loads(row["args"])),
            kwargs=json.loads(row["kwargs"]),
            enabled=row["enabled"],
            last_run_at=row["last_run_at"],
            next_run_at=row["next_run_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            description=row["description"],
            max_retries=row["max_retries"],
            retry_delay=row["retry_delay"],
            priority=row["priority"],
        )
