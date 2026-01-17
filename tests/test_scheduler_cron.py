"""Tests for cron expression parser and evaluator."""

import pytest
from datetime import datetime
from flowrra.scheduler.cron import CronExpression


class TestCronExpressionParsing:
    """Test cron expression parsing."""

    def test_parse_all_wildcards(self):
        """Test parsing expression with all wildcards."""
        cron = CronExpression("* * * * *")
        assert len(cron.minutes) == 60
        assert len(cron.hours) == 24
        assert len(cron.days) == 31
        assert len(cron.months) == 12
        assert len(cron.weekdays) == 7

    def test_parse_specific_values(self):
        """Test parsing specific values."""
        cron = CronExpression("30 9 15 6 1")
        assert cron.minutes == {30}
        assert cron.hours == {9}
        assert cron.days == {15}
        assert cron.months == {6}
        assert cron.weekdays == {1}

    def test_parse_ranges(self):
        """Test parsing ranges."""
        cron = CronExpression("0-5 9-17 1-7 * 1-5")
        assert cron.minutes == {0, 1, 2, 3, 4, 5}
        assert cron.hours == {9, 10, 11, 12, 13, 14, 15, 16, 17}
        assert cron.days == {1, 2, 3, 4, 5, 6, 7}
        assert cron.weekdays == {1, 2, 3, 4, 5}

    def test_parse_step_values(self):
        """Test parsing step values."""
        cron = CronExpression("*/15 */2 * * *")
        assert cron.minutes == {0, 15, 30, 45}
        assert cron.hours == {0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22}

    def test_parse_lists(self):
        """Test parsing comma-separated lists."""
        cron = CronExpression("0,15,30,45 9,12,15,18 1,15 * 1,3,5")
        assert cron.minutes == {0, 15, 30, 45}
        assert cron.hours == {9, 12, 15, 18}
        assert cron.days == {1, 15}
        assert cron.weekdays == {1, 3, 5}

    def test_parse_combined(self):
        """Test parsing combined expressions."""
        cron = CronExpression("0,30 9-17/2 1-15 * 1-5")
        assert cron.minutes == {0, 30}
        assert cron.hours == {9, 11, 13, 15, 17}

    def test_weekday_sunday_both_0_and_7(self):
        """Test that both 0 and 7 represent Sunday."""
        cron1 = CronExpression("0 0 * * 0")
        cron2 = CronExpression("0 0 * * 7")
        assert cron1.weekdays == {0}
        assert cron2.weekdays == {0}

    def test_invalid_field_count(self):
        """Test error on invalid field count."""
        with pytest.raises(ValueError, match="Expected 5 fields"):
            CronExpression("* * *")

        with pytest.raises(ValueError, match="Expected 5 fields"):
            CronExpression("* * * * * *")

    def test_invalid_range(self):
        """Test error on invalid range."""
        with pytest.raises(ValueError, match="Invalid range"):
            CronExpression("10-5 * * * *")


class TestCronExpressionMatching:
    """Test cron expression matching against datetime."""

    def test_matches_every_minute(self):
        """Test matching every minute."""
        cron = CronExpression("* * * * *")
        dt = datetime(2024, 6, 15, 10, 30)
        assert cron.matches(dt) is True

    def test_matches_specific_time(self):
        """Test matching specific time."""
        cron = CronExpression("30 9 15 6 *")
        assert cron.matches(datetime(2024, 6, 15, 9, 30)) is True
        assert cron.matches(datetime(2024, 6, 15, 9, 31)) is False
        assert cron.matches(datetime(2024, 6, 16, 9, 30)) is False

    def test_matches_weekday(self):
        """Test matching specific weekday."""
        # Monday (cron weekday 1, Python weekday 0)
        cron = CronExpression("0 9 * * 1")
        dt_monday = datetime(2024, 6, 17, 9, 0)  # June 17, 2024 is Monday
        dt_tuesday = datetime(2024, 6, 18, 9, 0)

        assert cron.matches(dt_monday) is True
        assert cron.matches(dt_tuesday) is False

    def test_matches_business_hours(self):
        """Test matching business hours (9-17 on weekdays)."""
        cron = CronExpression("0 9-17 * * 1-5")

        # Monday at 10 AM
        assert cron.matches(datetime(2024, 6, 17, 10, 0)) is True

        # Monday at 8 AM (before business hours)
        assert cron.matches(datetime(2024, 6, 17, 8, 0)) is False

        # Saturday at 10 AM (weekend)
        assert cron.matches(datetime(2024, 6, 22, 10, 0)) is False


class TestCronExpressionNextRun:
    """Test calculating next run time."""

    def test_next_run_simple(self):
        """Test next run calculation."""
        cron = CronExpression("30 9 * * *")
        after = datetime(2024, 6, 15, 8, 0)
        next_run = cron.next_run(after)

        assert next_run.hour == 9
        assert next_run.minute == 30
        assert next_run.day == 15

    def test_next_run_next_day(self):
        """Test next run on next day when time has passed."""
        cron = CronExpression("30 9 * * *")
        after = datetime(2024, 6, 15, 10, 0)  # After 9:30
        next_run = cron.next_run(after)

        assert next_run.day == 16
        assert next_run.hour == 9
        assert next_run.minute == 30

    def test_next_run_every_5_minutes(self):
        """Test next run for every 5 minutes."""
        cron = CronExpression("*/5 * * * *")
        after = datetime(2024, 6, 15, 10, 12)
        next_run = cron.next_run(after)

        assert next_run.hour == 10
        assert next_run.minute == 15

    def test_next_run_defaults_to_now(self):
        """Test next run defaults to current time."""
        cron = CronExpression("* * * * *")
        next_run = cron.next_run()

        # Should be within next few minutes
        now = datetime.now()
        assert (next_run - now).total_seconds() < 120


class TestCronExpressionString:
    """Test string representations."""

    def test_str(self):
        """Test string representation."""
        expr = "0 9 * * 1-5"
        cron = CronExpression(expr)
        assert str(cron) == expr

    def test_repr(self):
        """Test developer representation."""
        expr = "0 9 * * 1-5"
        cron = CronExpression(expr)
        assert repr(cron) == f"CronExpression('{expr}')"
