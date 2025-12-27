"""Tests for backend factory."""

import pytest
from flowrra.backends.factory import get_backend
from flowrra.backends.memory import InMemoryBackend
from flowrra.exceptions import BackendError


def test_factory_none_returns_memory():
    """Test that None returns InMemoryBackend."""
    backend = get_backend(None)

    assert isinstance(backend, InMemoryBackend)


def test_factory_passthrough_instance():
    """Test that backend instances are returned as-is."""
    backend = InMemoryBackend()
    result = get_backend(backend)

    assert result is backend


def test_factory_invalid_type():
    """Test error on invalid backend type."""
    with pytest.raises(BackendError, match="must be a connection string"):
        get_backend(123)


def test_factory_unsupported_scheme():
    """Test error on unsupported URL scheme."""
    with pytest.raises(BackendError, match="Unsupported backend URL scheme"):
        get_backend("postgres://localhost/db")


def test_factory_memory_scheme_not_supported():
    """Test that memory:// scheme is not supported."""
    with pytest.raises(BackendError, match="Unsupported backend URL scheme"):
        get_backend("memory://")


@pytest.mark.skipif(
    not __import__('importlib').util.find_spec('redis'),
    reason="Redis tests require 'redis' package"
)
def test_factory_redis_url():
    """Test creating RedisBackend from URL."""
    from flowrra.backends.redis import RedisBackend

    backend = get_backend("redis://localhost:6379/0")

    assert isinstance(backend, RedisBackend)


@pytest.mark.skipif(
    not __import__('importlib').util.find_spec('redis'),
    reason="Redis tests require 'redis' package"
)
def test_factory_rediss_url():
    """Test creating RedisBackend from SSL URL."""
    from flowrra.backends.redis import RedisBackend

    backend = get_backend("rediss://localhost:6379/0")

    assert isinstance(backend, RedisBackend)


@pytest.mark.skipif(
    not __import__('importlib').util.find_spec('redis'),
    reason="Redis tests require 'redis' package"
)
def test_factory_unix_socket_url():
    """Test creating RedisBackend from Unix socket URL."""
    from flowrra.backends.redis import RedisBackend

    backend = get_backend("unix:///tmp/redis.sock")

    assert isinstance(backend, RedisBackend)


def test_factory_redis_url_without_package(monkeypatch):
    """Test helpful error when redis package not installed."""
    import sys

    # Hide redis module
    redis_module = sys.modules.get('redis')
    redis_backends = sys.modules.get('flowrra.backends.redis')

    if redis_module:
        monkeypatch.setitem(sys.modules, 'redis', None)
    if redis_backends:
        monkeypatch.setitem(sys.modules, 'flowrra.backends.redis', None)

    # Clear the import cache to force reimport
    import importlib
    if 'flowrra.backends.factory' in sys.modules:
        importlib.reload(sys.modules['flowrra.backends.factory'])

    from flowrra.backends.factory import get_backend

    with pytest.raises(BackendError, match="requires redis package"):
        get_backend("redis://localhost:6379/0")
