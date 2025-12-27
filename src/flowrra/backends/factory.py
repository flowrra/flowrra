"""Backend factory for creating backends from connection strings."""

from urllib.parse import urlparse

from flowrra.backends.base import BaseResultBackend
from flowrra.backends.memory import InMemoryBackend
from flowrra.exceptions import BackendError


def get_backend(backend: BaseResultBackend | str | None, **kwargs) -> BaseResultBackend:
    """Create a backend from a connection string or return existing instance.

    This factory function provides a convenient way to create backends from
    connection strings while maintaining support for custom backend instances.
    Additional keyword arguments are passed to the backend constructor.

    Args:
        backend: Either a BaseResultBackend instance, a connection string, or None
        **kwargs: Additional backend-specific configuration options (ttl, max_connections, etc.)

    Returns:
        BaseResultBackend instance

    Raises:
        BackendError: If URL scheme is unsupported or backend creation fails

    Examples:
        # Redis connection string (recommended for production)
        backend = get_backend("redis://localhost:6379/0")
        backend = get_backend("rediss://localhost:6379/0", ttl=3600)  # With TTL

        # None returns InMemoryBackend (internal default)
        backend = get_backend(None)  # Returns InMemoryBackend()

        # Custom backend instance passthrough (advanced)
        backend = get_backend(custom_backend_instance)
    """
    if backend is None:
        return InMemoryBackend()

    if isinstance(backend, BaseResultBackend):
        return backend

    if not isinstance(backend, str):
        raise BackendError(
            f"Backend must be a connection string, BaseResultBackend instance, or None. "
            f"Got {type(backend).__name__}"
        )

    parsed = urlparse(backend)
    scheme = parsed.scheme.lower()

    if scheme in ("redis", "rediss", "unix"):
        try:
            from flowrra.backends.redis import RedisBackend
        except ImportError as e:
            raise BackendError(
                "Redis backend requires redis package. "
                "Install with: pip install flowrra[redis]"
            ) from e

        return RedisBackend(backend, **kwargs)

    else:
        raise BackendError(
            f"Unsupported backend URL scheme: '{scheme}'. "
            f"Supported schemes: redis, rediss, unix. "
            f"To add support for '{scheme}', implement a {scheme.title()}Backend class."
        )
