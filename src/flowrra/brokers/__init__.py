"""Flowrra task queue brokers.

Brokers handle task queueing and distribution (separate from result storage backends).

Available brokers:
    - RedisBroker: Distributed task queue using Redis lists
"""

from flowrra.brokers.base import BaseBroker

try:
    from flowrra.brokers.redis import RedisBroker
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

__all__ = [
    "BaseBroker",
]

if _HAS_REDIS:
    __all__.append("RedisBroker")
