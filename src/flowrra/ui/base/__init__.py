"""Base classes for Flowrra UI adapters.

This module provides the building blocks for creating framework-specific
UI adapters for Flowrra. It includes:

- BaseUIAdapter: Abstract adapter class for framework integration
- UIService: Service for UI page data aggregation
- ScheduleService: Service for schedule management operations
- Formatter: Static utility class for formatting values

These classes follow the Single Responsibility Principle and can be
composed to create adapters for different web frameworks (FastAPI,
Flask, Django, etc.).
"""

from flowrra.ui.base.adapter import BaseUIAdapter
from flowrra.ui.base.formatter import Formatter
from flowrra.ui.base.ui_service import UIService
from flowrra.ui.base.schedule_service import ScheduleService

__all__ = [
    "BaseUIAdapter",
    "Formatter",
    "UIService",
    "ScheduleService",
]
