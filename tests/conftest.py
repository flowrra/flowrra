"""Pytest configuration and fixtures for Flowrra tests."""

import pytest
import asyncio
from flowrra import IOExecutor, Config, ExecutorConfig
from flowrra.backends.memory import InMemoryBackend


@pytest.fixture
def io_executor():
    """Create a basic IOExecutor for testing."""
    config = Config(executor=ExecutorConfig(num_workers=2))
    return IOExecutor(config=config)


@pytest.fixture
def backend():
    """Create an in-memory backend for testing."""
    return InMemoryBackend()


@pytest.fixture
async def running_io_executor():
    """Create and start an IOExecutor, then clean up after test."""
    config = Config(executor=ExecutorConfig(num_workers=2))
    executor = IOExecutor(config=config)
    await executor.start()

    yield executor

    await executor.stop()


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)
