"""SQL backend for scheduler storage supporting PostgreSQL and MySQL.

This backend uses asyncpg for PostgreSQL and aiomysql for MySQL,
providing high-performance async database access for distributed deployments.
"""

import json
from datetime import datetime
from typing import List, Literal
from urllib.parse import urlparse

from flowrra.scheduler.backends.base import BaseSchedulerBackend
from flowrra.scheduler.models import ScheduledTask, ScheduleType


DatabaseType = Literal["postgresql", "mysql"]


class SQLSchedulerBackend(BaseSchedulerBackend):
    """SQL-based scheduler backend for PostgreSQL and MySQL.

    Features:
        - Supports PostgreSQL and MySQL
        - High-performance async operations
        - Connection pooling
        - Transaction support
        - Good for distributed/production deployments

    Args:
        url: Database connection URL
            - PostgreSQL: postgresql://user:pass@host:port/dbname
            - MySQL: mysql://user:pass@host:port/dbname
    """

    def __init__(self, url: str):
        """Initialize SQL backend.

        Args:
            url: Database connection URL

        Raises:
            ValueError: If URL scheme is not supported
        """
        self.url = url
        parsed = urlparse(url)
        self.scheme = parsed.scheme.lower()

        if self.scheme not in ("postgresql", "postgres", "mysql"):
            raise ValueError(
                f"Unsupported database scheme '{self.scheme}'. "
                f"Supported: postgresql, mysql"
            )

        self.db_type: DatabaseType = (
            "postgresql" if self.scheme in ("postgresql", "postgres") else "mysql"
        )

        self._pool = None

    async def _ensure_connected(self):
        """Ensure database connection pool exists."""
        if self._pool is None:
            if self.db_type == "postgresql":
                try:
                    import asyncpg
                except ImportError as e:
                    raise ImportError(
                        "PostgreSQL backend requires asyncpg package. "
                        "Install with: pip install flowrra[postgresql]"
                    ) from e

                self._pool = await asyncpg.create_pool(self.url)
            else:  # mysql
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
        if self.db_type == "postgresql":
            await self._create_postgresql_schema()
        else:
            await self._create_mysql_schema()

    async def _create_postgresql_schema(self) -> None:
        """Create PostgreSQL schema."""
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

    async def _create_mysql_schema(self) -> None:
        """Create MySQL schema."""
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
                        INDEX idx_next_run (next_run_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
            await conn.commit()

    async def create(self, task: ScheduledTask) -> None:
        """Create a new scheduled task."""
        pool = await self._ensure_connected()

        if self.db_type == "postgresql":
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
        else:  # mysql
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

        if self.db_type == "postgresql":
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
        else:  # mysql
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

        if self.db_type == "postgresql":
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM scheduled_tasks WHERE id = $1", task_id
                )
                return result != "DELETE 0"
        else:  # mysql
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

        if self.db_type == "postgresql":
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM scheduled_tasks WHERE id = $1", task_id
                )
                if row is None:
                    return None
                return self._pg_row_to_task(row)
        else:  # mysql
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
                    return self._mysql_row_to_task(dict(zip(columns, row)))

    async def list_all(self) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        pool = await self._ensure_connected()

        if self.db_type == "postgresql":
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM scheduled_tasks ORDER BY created_at")
                return [self._pg_row_to_task(row) for row in rows]
        else:  # mysql
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM scheduled_tasks ORDER BY created_at")
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [self._mysql_row_to_task(dict(zip(columns, row))) for row in rows]

    async def list_enabled(self) -> List[ScheduledTask]:
        """List only enabled scheduled tasks."""
        pool = await self._ensure_connected()

        if self.db_type == "postgresql":
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM scheduled_tasks WHERE enabled = TRUE ORDER BY next_run_at"
                )
                return [self._pg_row_to_task(row) for row in rows]
        else:  # mysql
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT * FROM scheduled_tasks WHERE enabled = TRUE ORDER BY next_run_at"
                    )
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [self._mysql_row_to_task(dict(zip(columns, row))) for row in rows]

    async def list_due(self, now: datetime | None = None) -> List[ScheduledTask]:
        """List tasks that are due for execution."""
        if now is None:
            now = datetime.now()

        pool = await self._ensure_connected()

        if self.db_type == "postgresql":
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM scheduled_tasks
                    WHERE enabled = TRUE AND next_run_at <= $1
                    ORDER BY priority DESC, next_run_at
                    """,
                    now,
                )
                return [self._pg_row_to_task(row) for row in rows]
        else:  # mysql
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
                    return [self._mysql_row_to_task(dict(zip(columns, row))) for row in rows]

    async def update_run_times(
        self, task_id: str, last_run: datetime, next_run: datetime
    ) -> None:
        """Update task run times after execution."""
        pool = await self._ensure_connected()

        if self.db_type == "postgresql":
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
        else:  # mysql
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

        if self.db_type == "postgresql":
            async with pool.acquire() as conn:
                result = await conn.execute("DELETE FROM scheduled_tasks")
                # Parse "DELETE N" to get count
                return int(result.split()[1]) if result else 0
        else:  # mysql
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("DELETE FROM scheduled_tasks")
                    count = cursor.rowcount
                await conn.commit()
                return count

    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool is not None:
            if self.db_type == "postgresql":
                await self._pool.close()
            else:  # mysql
                self._pool.close()
                await self._pool.wait_closed()
            self._pool = None

    def _pg_row_to_task(self, row) -> ScheduledTask:
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

    def _mysql_row_to_task(self, row: dict) -> ScheduledTask:
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
