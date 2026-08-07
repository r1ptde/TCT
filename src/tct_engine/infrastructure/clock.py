from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    def __init__(self, current_time: datetime) -> None:
        self._current_time = _require_aware_datetime(current_time)

    def now(self) -> datetime:
        return self._current_time


class ReplayClock:
    def __init__(self, start_time: datetime) -> None:
        self._current_time = _require_aware_datetime(start_time)

    def now(self) -> datetime:
        return self._current_time

    def advance_to(self, timestamp: datetime) -> None:
        timestamp = _require_aware_datetime(timestamp)

        if timestamp < self._current_time:
            raise ValueError("ReplayClock cannot move backwards.")

        self._current_time = timestamp


def _require_aware_datetime(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Timestamp must be timezone-aware.")

    return timestamp