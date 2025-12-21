"""Pytest configuration and fixtures for Flowrra tests."""

import pytest
import asyncio
from flowrra import AsyncTaskExecutor
from flowrra.backends.memory import InMemoryBackend


@pytest.fixture
def executor():
    """Create a basic executor for testing."""
    return AsyncTaskExecutor(num_workers=2)


@pytest.fixture
def backend():
    """Create an in-memory backend for testing."""
    return InMemoryBackend()


@pytest.fixture
async def running_executor():
    """Create and start an executor, then clean up after test."""
    executor = AsyncTaskExecutor(num_workers=2)
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
