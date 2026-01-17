"""Formatting utilities for Flowrra UI."""

from typing import Any

from flowrra.constants import STATUS_COLORS


class Formatter:
    """Static utility class for formatting values in the UI.

    Provides consistent formatting across all UI adapters:
    - Datetime formatting
    - Duration formatting
    - Status color mapping
    """

    @staticmethod
    def format_datetime(dt: Any) -> str:
        """Format datetime for display.

        Args:
            dt: Datetime object or ISO string

        Returns:
            Formatted datetime string
        """
        if dt is None:
            return "Never"

        if isinstance(dt, str):
            return dt

        # Handle datetime objects
        try:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except AttributeError:
            return str(dt)

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration (e.g., "2h 30m", "45s")
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    @staticmethod
    def get_status_color(status: str) -> str:
        """Get color class for task status.

        Args:
            status: Task status string

        Returns:
            CSS color class name
        """
        return STATUS_COLORS.get(status.lower(), "gray")
