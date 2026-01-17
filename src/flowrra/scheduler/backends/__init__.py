"""Scheduler storage backends."""

from flowrra.scheduler.backends.base import BaseSchedulerBackend
from flowrra.scheduler.backends.sqlite import SQLiteSchedulerBackend

__all__ = ["BaseSchedulerBackend", "SQLiteSchedulerBackend", "get_scheduler_backend"]


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

    elif scheme in ("postgresql", "postgres", "mysql"):
        try:
            from flowrra.scheduler.backends.sql import SQLSchedulerBackend
        except ImportError as e:
            db_name = "PostgreSQL" if scheme in ("postgresql", "postgres") else "MySQL"
            extra = "postgresql" if scheme in ("postgresql", "postgres") else "mysql"
            raise ImportError(
                f"{db_name} backend requires additional packages. "
                f"Install with: pip install flowrra[{extra}]"
            ) from e

        return SQLSchedulerBackend(url)

    else:
        raise ValueError(
            f"Unsupported scheduler backend URL scheme: '{scheme}'. "
            f"Supported schemes: sqlite, postgresql, mysql"
        )
