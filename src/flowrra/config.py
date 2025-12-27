import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrokerConfig:
    url: str
    max_connections: int = 50
    socket_timeout: float = 5.0
    retry_on_timeout: bool = True

    def __post_init__(self):
        """Validate broker configuration."""
        if not self.url:
            raise ValueError("Broker URL is required")

        if self.max_connections < 1:
            raise ValueError("max_connections must be at least 1")

        if self.socket_timeout < 0:
            raise ValueError("socket_timeout must be non-negative")

    def create_broker(self) -> "BaseBroker":
        """Create broker instance from this configuration.

        Returns:
            Broker instance

        Raises:
            BrokerError: If URL scheme is unsupported or creation fails
        """
        from flowrra.brokers.factory import get_broker

        return get_broker(
            self.url,
            max_connections=self.max_connections,
            socket_timeout=self.socket_timeout,
            retry_on_timeout=self.retry_on_timeout,
        )


@dataclass
class BackendConfig:
    url: str
    ttl: int | None = None
    max_connections: int = 50
    socket_timeout: float = 5.0
    retry_on_timeout: bool = True

    def __post_init__(self):
        """Validate backend configuration."""
        if not self.url:
            raise ValueError("Backend URL is required")

        if self.ttl is not None and self.ttl < 1:
            raise ValueError("ttl must be at least 1 second")

        if self.max_connections < 1:
            raise ValueError("max_connections must be at least 1")

        if self.socket_timeout < 0:
            raise ValueError("socket_timeout must be non-negative")

    def create_backend(self) -> "BaseResultBackend":
        """Create backend instance from this configuration.

        Returns:
            Backend instance

        Raises:
            BackendError: If URL scheme is unsupported or creation fails
        """
        from flowrra.backends.factory import get_backend

        return get_backend(
            self.url,
            ttl=self.ttl,
            max_connections=self.max_connections,
            socket_timeout=self.socket_timeout,
            retry_on_timeout=self.retry_on_timeout,
        )


@dataclass
class ExecutorConfig:
    num_workers: int = 4
    cpu_workers: int | None = None
    max_queue_size: int = 1000
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        """Validate executor configuration."""
        if self.num_workers < 1:
            raise ValueError("num_workers must be at least 1")

        if self.cpu_workers is not None and self.cpu_workers < 1:
            raise ValueError("cpu_workers must be at least 1")

        if self.max_queue_size < 1:
            raise ValueError("max_queue_size must be at least 1")

        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")


@dataclass
class Config:
    """Main Flowrra configuration aggregating component configs.

    This class brings together broker, backend, and executor configurations
    into a single, structured configuration object. All components are optional
    with sensible defaults.

    Args:
        broker: Broker configuration for task queueing (optional, uses asyncio.PriorityQueue if None)
        backend: Backend configuration for result storage (optional)
        executor: Executor configuration (optional, defaults to ExecutorConfig())
    """
    broker: BrokerConfig | None = None
    backend: BackendConfig | None = None
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)

    def __post_init__(self):
        """Ensure executor config exists."""
        if self.executor is None:
            self.executor = ExecutorConfig()

    def create_broker(self) -> "BaseBroker | None":
        """Create broker instance from configuration.

        Returns:
            Broker instance if configured, None otherwise
        """
        from flowrra.brokers.factory import get_broker

        if self.broker is not None:
            return self.broker.create_broker()
        else:
            return get_broker(None)

    def create_backend(self) -> "BaseResultBackend":
        """Create backend instance from configuration.

        Returns:
            Backend instance if configured, InMemory otherwise
        """
        from flowrra.backends.factory import get_backend

        if self.backend is not None:
            return self.backend.create_backend()
        else:
            return get_backend(None)

    @classmethod
    def from_env(cls, prefix: str = "FLOWRRA_") -> "Config":
        """Load configuration from environment variables using mappings."""
        env_cache: dict[str, str | None] = {}

        def get_env(key: str, default: Any = None, type_cast: type = str) -> Any:
            env_key = f"{prefix}{key.upper()}"
            if env_key not in env_cache:
                env_cache[env_key] = os.getenv(env_key)

            value = env_cache[env_key]

            if value is None:
                return default
            if type_cast == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif type_cast == int:
                return int(value)
            elif type_cast == float:
                return float(value)
            else:
                return value

        broker_map = {
            "url": ("broker_url", str, None),
            "max_connections": ("broker_max_connections", int, 50),
            "socket_timeout": ("broker_socket_timeout", float, 5.0),
            "retry_on_timeout": ("broker_retry_on_timeout", bool, True),
        }

        backend_map = {
            "url": ("backend_url", str, None),
            "ttl": ("backend_ttl", int, None),
            "max_connections": ("backend_max_connections", int, 50),
            "socket_timeout": ("backend_socket_timeout", float, 5.0),
            "retry_on_timeout": ("backend_retry_on_timeout", bool, True),
        }

        executor_map = {
            "num_workers": ("executor_num_workers", int, 4),
            "cpu_workers": ("executor_cpu_workers", int, None),
            "max_queue_size": ("executor_max_queue_size", int, 1000),
            "max_retries": ("executor_max_retries", int, 3),
            "retry_delay": ("executor_retry_delay", float, 1.0),
        }

        def build_config(map_def):
            kwargs = {}
            for field, (env_name, type_cast, default) in map_def.items():
                val = get_env(env_name, default=default, type_cast=type_cast)
                kwargs[field] = val
            return kwargs

        broker_kwargs = build_config(broker_map)
        broker = BrokerConfig(**broker_kwargs) if broker_kwargs["url"] else None

        backend_kwargs = build_config(backend_map)
        backend = BackendConfig(**backend_kwargs) if backend_kwargs["url"] else None

        executor_kwargs = build_config(executor_map)
        executor = ExecutorConfig(**executor_kwargs)

        return cls(broker=broker, backend=backend, executor=executor)
