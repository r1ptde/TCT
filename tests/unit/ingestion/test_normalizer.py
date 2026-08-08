from datetime import UTC, datetime, timedelta, timezone

import pytest

from tct_engine.ingestion.models import RawTick
from tct_engine.ingestion.normalizer import TickNormalizer


def test_normalizer_canonicalizes_instrument() -> None:
    raw_tick = RawTick(
        instrument=" eurusd ",
        timestamp=datetime(2026, 8, 8, 8, 0, tzinfo=UTC),
        bid=1.1500,
        ask=1.1502,
    )

    tick = TickNormalizer().normalize(raw_tick)

    assert tick.instrument == "EURUSD"


def test_normalizer_converts_timestamp_to_utc() -> None:
    bst = timezone(timedelta(hours=1))

    raw_tick = RawTick(
        instrument="EURUSD",
        timestamp=datetime(2026, 8, 8, 9, 0, tzinfo=bst),
        bid=1.1500,
        ask=1.1502,
    )

    tick = TickNormalizer().normalize(raw_tick)

    assert tick.timestamp == datetime(2026, 8, 8, 8, 0, tzinfo=UTC)


def test_normalizer_rejects_naive_datetime() -> None:
    raw_tick = RawTick(
        instrument="EURUSD",
        timestamp=datetime(2026, 8, 8, 8, 0),  # noqa: DTZ001
        bid=1.1500,
        ask=1.1502,
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        TickNormalizer().normalize(raw_tick)
