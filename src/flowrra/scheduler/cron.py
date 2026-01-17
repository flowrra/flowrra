"""Cron expression parser and evaluator.

Supports standard cron syntax:
    - Minute (0-59)
    - Hour (0-23)
    - Day of month (1-31)
    - Month (1-12)
    - Day of week (0-7, where 0 and 7 are Sunday)

Special characters:
    - * (any value)
    - , (value list separator)
    - - (range of values)
    - / (step values)

Examples:
    "*/5 * * * *" - Every 5 minutes
    "0 */2 * * *" - Every 2 hours
    "0 9 * * 1-5" - 9 AM on weekdays
    "0 0 1 * *" - First day of every month at midnight
"""

from datetime import datetime, timedelta
from typing import Set


class CronExpression:
    """Parse and evaluate cron expressions."""

    def __init__(self, expression: str):
        """Initialize cron expression.

        Args:
            expression: Cron expression string (5 fields: minute hour day month weekday)

        Raises:
            ValueError: If expression format is invalid
        """
        self.expression = expression.strip()
        parts = self.expression.split()

        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression '{expression}'. "
                f"Expected 5 fields (minute hour day month weekday), got {len(parts)}"
            )

        self.minute_field = parts[0]
        self.hour_field = parts[1]
        self.day_field = parts[2]
        self.month_field = parts[3]
        self.weekday_field = parts[4]

        # Pre-parse fields for efficiency
        self.minutes = self._parse_field(self.minute_field, 0, 59)
        self.hours = self._parse_field(self.hour_field, 0, 23)
        self.days = self._parse_field(self.day_field, 1, 31)
        self.months = self._parse_field(self.month_field, 1, 12)
        self.weekdays = self._parse_weekday_field(self.weekday_field)

    def _parse_field(self, field: str, min_val: int, max_val: int) -> Set[int]:
        """Parse a cron field into a set of valid values.

        Args:
            field: Cron field string (e.g., "*/5", "1-10", "1,3,5")
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Set of valid integer values

        Raises:
            ValueError: If field format is invalid
        """
        if field == "*":
            return set(range(min_val, max_val + 1))

        values = set()

        for part in field.split(","):
            if "/" in part:
                # Step values: */5 or 10-20/2
                range_part, step = part.split("/")
                step_val = int(step)

                if range_part == "*":
                    start, end = min_val, max_val
                elif "-" in range_part:
                    start_str, end_str = range_part.split("-")
                    start, end = int(start_str), int(end_str)
                else:
                    start = int(range_part)
                    end = max_val

                for val in range(start, end + 1, step_val):
                    if min_val <= val <= max_val:
                        values.add(val)

            elif "-" in part:
                # Range: 1-5
                start_str, end_str = part.split("-")
                start, end = int(start_str), int(end_str)

                if start > end:
                    raise ValueError(f"Invalid range: {part} (start > end)")

                for val in range(start, end + 1):
                    if min_val <= val <= max_val:
                        values.add(val)

            else:
                # Single value
                val = int(part)
                if min_val <= val <= max_val:
                    values.add(val)
                else:
                    raise ValueError(f"Value {val} out of range [{min_val}, {max_val}]")

        return values

    def _parse_weekday_field(self, field: str) -> Set[int]:
        """Parse weekday field, treating both 0 and 7 as Sunday.

        Args:
            field: Weekday field string

        Returns:
            Set of valid weekday integers (0-6, where 0 is Sunday)
        """
        weekdays = self._parse_field(field, 0, 7)

        # Convert 7 (Sunday) to 0
        if 7 in weekdays:
            weekdays.remove(7)
            weekdays.add(0)

        return weekdays

    def matches(self, dt: datetime) -> bool:
        """Check if datetime matches the cron expression.

        Args:
            dt: Datetime to check

        Returns:
            True if datetime matches the cron schedule
        """
        # Convert Python weekday (0=Monday) to cron weekday (0=Sunday, 1=Monday)
        # Python: Mon=0, Tue=1, ..., Sun=6
        # Cron: Sun=0, Mon=1, Tue=2, ..., Sat=6
        cron_weekday = (dt.weekday() + 1) % 7

        return (
            dt.minute in self.minutes
            and dt.hour in self.hours
            and dt.day in self.days
            and dt.month in self.months
            and cron_weekday in self.weekdays
        )

    def next_run(self, after: datetime | None = None) -> datetime:
        """Calculate the next run time after the given datetime.

        Args:
            after: Starting datetime (defaults to now)

        Returns:
            Next datetime matching the cron expression
        """
        if after is None:
            after = datetime.now()

        # Start from the next minute
        current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Limit search to prevent infinite loops (max 3 years)
        max_iterations = 525600 * 3  # minutes in 3 years

        for _ in range(max_iterations):
            if self.matches(current):
                return current

            # Move to next minute
            current += timedelta(minutes=1)

        raise ValueError(
            f"Could not find next run time for cron expression '{self.expression}' "
            f"within 4 years from {after}"
        )

    def __str__(self) -> str:
        """String representation."""
        return self.expression

    def __repr__(self) -> str:
        """Developer representation."""
        return f"CronExpression('{self.expression}')"
