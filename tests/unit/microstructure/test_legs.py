from datetime import UTC, datetime, timedelta

import pytest

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.legs import (
    LegDirection,
    StructuralLegDetector,
)


def make_candle(
    index: int,
    *,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    open_time = datetime(2026, 8, 10, 8, 0, tzinfo=UTC) + timedelta(minutes=index)

    return Candle(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=open_price,
        high=high,
        low=low,
        close=close,
        tick_volume=10,
        is_closed=True,
    )


def test_detects_valid_bearish_leg() -> None:
    detector = StructuralLegDetector()

    first = make_candle(
        0,
        open_price=1.1010,
        high=1.1020,
        low=1.1000,
        close=1.1005,
    )

    second = make_candle(
        1,
        open_price=1.1008,
        high=1.1015,
        low=1.0990,
        close=1.0995,
    )

    assert detector.process_bar(first) is None

    detection = detector.process_bar(second)

    assert detection is not None
    assert detection.direction is LegDirection.BEARISH
    assert detection.first_candle == first
    assert detection.second_candle == second


def test_bearish_second_candle_may_take_first_high() -> None:
    detector = StructuralLegDetector()

    first = make_candle(
        0,
        open_price=1.1010,
        high=1.1020,
        low=1.1000,
        close=1.1005,
    )

    second = make_candle(
        1,
        open_price=1.1015,
        high=1.1030,
        low=1.0990,
        close=1.0995,
    )

    detector.process_bar(first)
    detection = detector.process_bar(second)

    assert detection is not None
    assert detection.direction is LegDirection.BEARISH


def test_bearish_pair_requires_lower_low() -> None:
    detector = StructuralLegDetector()

    first = make_candle(
        0,
        open_price=1.1010,
        high=1.1020,
        low=1.1000,
        close=1.1005,
    )

    second = make_candle(
        1,
        open_price=1.1008,
        high=1.1010,
        low=1.1000,
        close=1.1001,
    )

    detector.process_bar(first)

    assert detector.process_bar(second) is None


def test_detects_valid_bullish_leg() -> None:
    detector = StructuralLegDetector()

    first = make_candle(
        0,
        open_price=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )

    second = make_candle(
        1,
        open_price=1.1002,
        high=1.1020,
        low=1.0995,
        close=1.1015,
    )

    detector.process_bar(first)
    detection = detector.process_bar(second)

    assert detection is not None
    assert detection.direction is LegDirection.BULLISH


def test_bullish_second_candle_may_take_first_low() -> None:
    detector = StructuralLegDetector()

    first = make_candle(
        0,
        open_price=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )

    second = make_candle(
        1,
        open_price=1.0995,
        high=1.1020,
        low=1.0980,
        close=1.1015,
    )

    detector.process_bar(first)
    detection = detector.process_bar(second)

    assert detection is not None
    assert detection.direction is LegDirection.BULLISH


def test_bullish_pair_requires_higher_high() -> None:
    detector = StructuralLegDetector()

    first = make_candle(
        0,
        open_price=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )

    second = make_candle(
        1,
        open_price=1.1002,
        high=1.1010,
        low=1.0995,
        close=1.1008,
    )

    detector.process_bar(first)

    assert detector.process_bar(second) is None


def test_mixed_candles_do_not_form_leg() -> None:
    detector = StructuralLegDetector()

    bullish = make_candle(
        0,
        open_price=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )

    bearish = make_candle(
        1,
        open_price=1.1008,
        high=1.1010,
        low=1.0990,
        close=1.0995,
    )

    detector.process_bar(bullish)

    assert detector.process_bar(bearish) is None


def test_doji_breaks_strong_sequence() -> None:
    detector = StructuralLegDetector()

    bearish = make_candle(
        0,
        open_price=1.1010,
        high=1.1020,
        low=1.1000,
        close=1.1005,
    )

    doji = make_candle(
        1,
        open_price=1.1005,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )

    detector.process_bar(bearish)

    assert detector.process_bar(doji) is None


def test_open_bar_is_rejected() -> None:
    detector = StructuralLegDetector()

    candle = make_candle(
        0,
        open_price=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )

    open_candle = Candle(
        instrument=candle.instrument,
        timeframe=candle.timeframe,
        open_time=candle.open_time,
        close_time=candle.close_time,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        tick_volume=candle.tick_volume,
        is_closed=False,
    )

    with pytest.raises(ValueError, match="closed candle"):
        detector.process_bar(open_candle)
