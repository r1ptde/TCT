from datetime import UTC, datetime, timedelta

import pytest

from tct_engine.infrastructure.clock import FixedClock, ReplayClock, SystemClock


def test_fixed_clock_returns_fixed_time() -> None:
    timestamp = datetime(2026, 8, 7, 8, 0, tzinfo=UTC)

    clock = FixedClock(timestamp)

    assert clock.now() == timestamp


def test_replay_clock_can_advance() -> None:
    start = datetime(2026, 8, 7, 8, 0, tzinfo=UTC)
    later = start + timedelta(minutes=15)

    clock = ReplayClock(start)
    clock.advance_to(later)

    assert clock.now() == later


def test_replay_clock_cannot_move_backwards() -> None:
    start = datetime(2026, 8, 7, 8, 0, tzinfo=UTC)
    earlier = start - timedelta(seconds=1)

    clock = ReplayClock(start)

    with pytest.raises(ValueError, match="cannot move backwards"):
        clock.advance_to(earlier)


def test_fixed_clock_rejects_naive_datetime() -> None:
    timestamp = datetime(2026, 8, 7, 8, 0)  # noqa: DTZ001 - intentionally naive

    with pytest.raises(ValueError, match="timezone-aware"):
        FixedClock(timestamp)


def test_system_clock_is_timezone_aware() -> None:
    timestamp = SystemClock().now()

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() is not None
