"""Factory for creating broker instances from connection strings."""

from urllib.parse import urlparse
from flowrra.brokers.base import BaseBroker
from flowrra.exceptions import BackendError


def get_broker(broker: BaseBroker | str | None, **kwargs) -> BaseBroker | None:
    """Create a broker from a connection string or return existing instance.

    This factory function provides a convenient way to create brokers from
    connection strings while maintaining support for custom broker instances.
    Additional keyword arguments are passed to the broker constructor.

    Args:
        broker: Either a BaseBroker instance, a connection string, or None
        **kwargs: Additional broker-specific configuration options (max_connections, etc.)

    Returns:
        BaseBroker instance if provided, None if broker is None

    Raises:
        BackendError: If URL scheme is unsupported or broker creation fails

    Examples:
        # Redis connection string
        broker = get_broker("redis://localhost:6379/0")
        broker = get_broker("redis://localhost:6379/0", max_connections=100)

        # None returns None (use asyncio.PriorityQueue)
        broker = get_broker(None)  # Returns None

        # Custom broker instance passthrough
        broker = get_broker(custom_broker_instance)
    """
    if broker is None:
        return None

    if isinstance(broker, BaseBroker):
        return broker

    if not isinstance(broker, str):
        raise BackendError(
            f"Broker must be a connection string, BaseBroker instance, or None. "
            f"Got {type(broker).__name__}"
        )

    parsed = urlparse(broker)
    scheme = parsed.scheme.lower()

    if scheme in ("redis", "rediss", "unix"):
        try:
            from flowrra.brokers.redis import RedisBroker
        except ImportError as e:
            raise BackendError(
                "Redis broker requires redis package. "
                "Install with: pip install flowrra[redis]"
            ) from e

        return RedisBroker(broker, **kwargs)

    elif scheme == "amqp" or scheme == "amqps":
        raise BackendError(
            f"RabbitMQ/AMQP broker support not yet implemented. "
            f"To add support, implement a RabbitMQBroker class."
        )

    else:
        raise BackendError(
            f"Unsupported broker URL scheme: '{scheme}'. "
            f"Supported schemes: redis, rediss, unix. "
            f"To add support for '{scheme}', implement a {scheme.title()}Broker class."
        )
