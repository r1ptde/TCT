from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.structural_points import (
    StructuralPointDetector,
    StructuralPointSide,
)


def make_candle(
    index: int,
    *,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    open_time = datetime(
        2026,
        8,
        12,
        8,
        0,
        tzinfo=UTC,
    ) + timedelta(minutes=index)

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


def test_establishes_structural_low_after_recovery_to_initiating_high() -> None:
    detector = StructuralPointDetector()

    candles = [
        make_candle(
            0,
            open_price=1.1050,
            high=1.1060,
            low=1.1030,
            close=1.1040,
        ),
        make_candle(
            1,
            open_price=1.1040,
            high=1.1050,
            low=1.1010,
            close=1.1020,
        ),
        make_candle(
            2,
            open_price=1.1020,
            high=1.1030,
            low=1.0990,
            close=1.1000,
        ),
        make_candle(
            3,
            open_price=1.1000,
            high=1.1020,
            low=1.0980,
            close=1.1010,
        ),
        make_candle(
            4,
            open_price=1.1010,
            high=1.1040,
            low=1.1000,
            close=1.1030,
        ),
        make_candle(
            5,
            open_price=1.1030,
            high=1.1060,
            low=1.1020,
            close=1.1050,
        ),
    ]

    point = None

    for candle in candles:
        result = detector.process_bar(candle)

        if result is not None:
            point = result

    assert point is not None
    assert point.side is StructuralPointSide.LOW
    assert point.price == 1.0980


def test_candidate_low_updates_before_establishment() -> None:
    detector = StructuralPointDetector()

    candles = [
        make_candle(
            0,
            open_price=1.1050,
            high=1.1060,
            low=1.1030,
            close=1.1040,
        ),
        make_candle(
            1,
            open_price=1.1040,
            high=1.1050,
            low=1.1010,
            close=1.1020,
        ),
        make_candle(
            2,
            open_price=1.1020,
            high=1.1030,
            low=1.0990,
            close=1.1000,
        ),
        make_candle(
            3,
            open_price=1.1000,
            high=1.1010,
            low=1.0970,
            close=1.0990,
        ),
        make_candle(
            4,
            open_price=1.0990,
            high=1.1020,
            low=1.0980,
            close=1.1010,
        ),
        make_candle(
            5,
            open_price=1.1010,
            high=1.1040,
            low=1.1000,
            close=1.1030,
        ),
        make_candle(
            6,
            open_price=1.1030,
            high=1.1060,
            low=1.1020,
            close=1.1050,
        ),
    ]

    points = []

    for candle in candles:
        point = detector.process_bar(candle)

        if point is not None:
            points.append(point)

    assert len(points) == 1
    assert points[0].price == 1.0970


def test_bullish_leg_alone_does_not_establish_low() -> None:
    detector = StructuralPointDetector()

    candles = [
        make_candle(
            0,
            open_price=1.1050,
            high=1.1060,
            low=1.1030,
            close=1.1040,
        ),
        make_candle(
            1,
            open_price=1.1040,
            high=1.1050,
            low=1.1010,
            close=1.1020,
        ),
        make_candle(
            2,
            open_price=1.1020,
            high=1.1030,
            low=1.0990,
            close=1.1010,
        ),
        make_candle(
            3,
            open_price=1.1010,
            high=1.1040,
            low=1.1000,
            close=1.1030,
        ),
    ]

    points = [point for candle in candles if (point := detector.process_bar(candle)) is not None]

    assert points == []


def test_first_bearish_candle_wick_can_define_initiating_high() -> None:
    detector = StructuralPointDetector()

    candles = [
        make_candle(
            0,
            open_price=1.1040,
            high=1.1070,
            low=1.1020,
            close=1.1030,
        ),
        make_candle(
            1,
            open_price=1.1030,
            high=1.1040,
            low=1.1000,
            close=1.1010,
        ),
        make_candle(
            2,
            open_price=1.1010,
            high=1.1020,
            low=1.0980,
            close=1.1000,
        ),
        make_candle(
            3,
            open_price=1.1000,
            high=1.1040,
            low=1.0990,
            close=1.1030,
        ),
        make_candle(
            4,
            open_price=1.1030,
            high=1.1060,
            low=1.1020,
            close=1.1050,
        ),
    ]

    for candle in candles:
        assert detector.process_bar(candle) is None

    touch = make_candle(
        5,
        open_price=1.1050,
        high=1.1070,
        low=1.1040,
        close=1.1060,
    )

    point = detector.process_bar(touch)

    assert point is not None
    assert point.side is StructuralPointSide.LOW


def test_structural_high_logic_is_symmetric() -> None:
    detector = StructuralPointDetector()

    candles = [
        make_candle(
            0,
            open_price=1.1000,
            high=1.1030,
            low=1.0990,
            close=1.1020,
        ),
        make_candle(
            1,
            open_price=1.1020,
            high=1.1050,
            low=1.1010,
            close=1.1040,
        ),
        make_candle(
            2,
            open_price=1.1040,
            high=1.1070,
            low=1.1030,
            close=1.1060,
        ),
        make_candle(
            3,
            open_price=1.1060,
            high=1.1080,
            low=1.1040,
            close=1.1050,
        ),
        make_candle(
            4,
            open_price=1.1050,
            high=1.1060,
            low=1.1010,
            close=1.1020,
        ),
        make_candle(
            5,
            open_price=1.1020,
            high=1.1030,
            low=1.0990,
            close=1.1000,
        ),
    ]

    point = None

    for candle in candles:
        result = detector.process_bar(candle)

        if result is not None:
            point = result

    assert point is not None
    assert point.side is StructuralPointSide.HIGH
    assert point.price == 1.1080
