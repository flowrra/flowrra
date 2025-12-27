"""Basic tests for broker functionality."""

import pytest
from flowrra import IOExecutor, Config, BrokerConfig, BackendConfig, ExecutorConfig
from flowrra.task import TaskStatus


class TestBrokerBasicConfig:
    """Test basic broker configuration."""

    def test_broker_config_creation(self):
        """Test creating broker configuration."""
        broker = BrokerConfig(url='redis://localhost:6379/0')

        assert broker.url == 'redis://localhost:6379/0'
        assert broker.max_connections == 50
        assert broker.socket_timeout == 5.0
        assert broker.retry_on_timeout is True

    def test_broker_config_custom_settings(self):
        """Test broker configuration with custom settings."""
        broker = BrokerConfig(
            url='redis://localhost:6379/0',
            max_connections=100,
            socket_timeout=10.0,
            retry_on_timeout=False
        )

        assert broker.max_connections == 100
        assert broker.socket_timeout == 10.0
        assert broker.retry_on_timeout is False

    def test_broker_config_validation(self):
        """Test broker configuration validation."""
        with pytest.raises(ValueError, match="Broker URL is required"):
            BrokerConfig(url='')

        with pytest.raises(ValueError, match="max_connections must be at least 1"):
            BrokerConfig(url='redis://localhost:6379/0', max_connections=0)

        with pytest.raises(ValueError, match="socket_timeout must be non-negative"):
            BrokerConfig(url='redis://localhost:6379/0', socket_timeout=-1)


class TestConfigWithBroker:
    """Test Config with broker support."""

    def test_config_with_broker(self):
        """Test creating config with broker."""
        config = Config(
            broker=BrokerConfig(url='redis://localhost:6379/0'),
            backend=BackendConfig(url='redis://localhost:6379/1'),
            executor=ExecutorConfig(num_workers=8)
        )

        assert config.broker is not None
        assert config.broker.url == 'redis://localhost:6379/0'
        assert config.backend is not None
        assert config.backend.url == 'redis://localhost:6379/1'
        assert config.executor.num_workers == 8

    def test_config_without_broker(self):
        """Test creating config without broker."""
        config = Config(
            backend=BackendConfig(url='redis://localhost:6379/1')
        )

        assert config.broker is None
        assert config.backend is not None


class TestIOExecutorWithConfig:
    """Test IOExecutor with config and broker support."""

    @pytest.mark.asyncio
    async def test_io_executor_with_config(self):
        """Test IOExecutor accepts config parameter."""
        config = Config(
            executor=ExecutorConfig(num_workers=2)
        )

        executor = IOExecutor(config=config)

        assert executor._num_workers == 2
        assert executor._config is not None

    @pytest.mark.asyncio
    async def test_io_executor_different_worker_counts(self):
        """Test IOExecutor with different worker counts."""
        config1 = Config(executor=ExecutorConfig(num_workers=2))
        config2 = Config(executor=ExecutorConfig(num_workers=8))

        executor1 = IOExecutor(config=config1)
        executor2 = IOExecutor(config=config2)

        assert executor1._num_workers == 2
        assert executor2._num_workers == 8

    @pytest.mark.asyncio
    async def test_io_executor_with_backend_config(self):
        """Test IOExecutor with backend configuration."""
        # Without broker (uses asyncio.PriorityQueue)
        config = Config(
            backend=BackendConfig(url='redis://localhost:6379/1')
        )
        executor = IOExecutor(config=config)

        assert executor._num_workers == 4  # Default from ExecutorConfig
        assert executor._config is not None
        assert executor._config.backend is not None
        assert executor._config.backend.url == 'redis://localhost:6379/1'
        assert executor._config.broker is None  # No broker

    @pytest.mark.asyncio
    async def test_io_executor_with_broker_and_backend(self):
        """Test IOExecutor with both broker and backend."""
        config = Config(
            broker=BrokerConfig(url='redis://localhost:6379/0'),
            backend=BackendConfig(url='redis://localhost:6379/1')
        )
        executor = IOExecutor(config=config)

        assert executor._config.broker is not None
        assert executor._config.broker.url == 'redis://localhost:6379/0'
        assert executor._config.backend is not None
        assert executor._config.backend.url == 'redis://localhost:6379/1'
        assert executor._num_workers == 4  # Default from ExecutorConfig

    @pytest.mark.asyncio
    async def test_io_executor_without_broker_uses_priority_queue(self):
        """Test IOExecutor without broker uses asyncio.PriorityQueue."""
        config = Config(executor=ExecutorConfig(num_workers=2))
        executor = IOExecutor(config=config)

        # Should use asyncio.PriorityQueue (broker is None)
        assert executor.broker is None
        assert executor._queue is not None  # Priority queue exists

        @executor.task()
        async def simple_task(x: int):
            return x * 2

        async with executor:
            task_id = await executor.submit(simple_task, 21)
            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.status == TaskStatus.SUCCESS
            assert result.result == 42


class TestConfigFromEnv:
    """Test Config.from_env() with broker support."""

    def test_config_from_env_with_broker(self, monkeypatch):
        """Test loading broker config from environment."""
        monkeypatch.setenv("FLOWRRA_BROKER_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("FLOWRRA_BACKEND_URL", "redis://localhost:6379/1")
        monkeypatch.setenv("FLOWRRA_EXECUTOR_NUM_WORKERS", "8")

        config = Config.from_env()

        assert config.broker is not None
        assert config.broker.url == "redis://localhost:6379/0"
        assert config.backend is not None
        assert config.backend.url == "redis://localhost:6379/1"
        assert config.executor.num_workers == 8

    def test_config_from_env_without_broker(self, monkeypatch):
        """Test loading config from environment without broker."""
        monkeypatch.setenv("FLOWRRA_BACKEND_URL", "redis://localhost:6379/1")
        monkeypatch.setenv("FLOWRRA_EXECUTOR_NUM_WORKERS", "4")

        config = Config.from_env()

        assert config.broker is None
        assert config.backend is not None
        assert config.executor.num_workers == 4
