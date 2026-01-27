"""Scheduler storage backends."""

from flowrra.scheduler.backends.base import BaseSchedulerBackend
from flowrra.scheduler.backends.sqlite import SQLiteSchedulerBackend
from flowrra.scheduler.backends.postgresql import PostgreSQLSchedulerBackend
from flowrra.scheduler.backends.mysql import MySQLSchedulerBackend

__all__ = [
    "BaseSchedulerBackend",
    "SQLiteSchedulerBackend",
    "PostgreSQLSchedulerBackend",
    "MySQLSchedulerBackend",
    "get_scheduler_backend",
]


def get_scheduler_backend(url: str | None = None) -> BaseSchedulerBackend:
    """Create a scheduler backend from a database URL.

    Args:
        url: Database connection URL or None for default SQLite

    Returns:
        Scheduler backend instance

    Raises:
        ValueError: If URL scheme is unsupported

    Supported URLs:
        - None or "sqlite://..." - SQLite backend (default: .flowrra_schedule.db)
        - "postgresql://..." - PostgreSQL backend
        - "mysql://..." - MySQL backend

    Examples:
        # Default SQLite
        backend = get_scheduler_backend()

        # Custom SQLite path
        backend = get_scheduler_backend("sqlite:///path/to/schedule.db")

        # PostgreSQL
        backend = get_scheduler_backend("postgresql://user:pass@localhost/flowrra")

        # MySQL
        backend = get_scheduler_backend("mysql://user:pass@localhost/flowrra")
    """
    from urllib.parse import urlparse

    if url is None:
        return SQLiteSchedulerBackend()

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme == "sqlite" or not scheme:
        if parsed.path:
            # Remove leading slash for local paths
            path = parsed.path.lstrip("/") if parsed.path.startswith("/") else parsed.path
            return SQLiteSchedulerBackend(database_path=path)
        else:
            return SQLiteSchedulerBackend()

    elif scheme in ("postgresql", "postgres"):
        try:
            return PostgreSQLSchedulerBackend(url)
        except ImportError as e:
            raise ImportError(
                "PostgreSQL backend requires additional packages. "
                "Install with: pip install flowrra[postgresql]"
            ) from e

    elif scheme == "mysql":
        try:
            return MySQLSchedulerBackend(url)
        except ImportError as e:
            raise ImportError(
                "MySQL backend requires additional packages. "
                "Install with: pip install flowrra[mysql]"
            ) from e

    else:
        raise ValueError(
            f"Unsupported scheduler backend URL scheme: '{scheme}'. "
            f"Supported schemes: sqlite, postgresql, mysql"
        )
