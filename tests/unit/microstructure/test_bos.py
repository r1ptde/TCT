from datetime import UTC, datetime, timedelta

import pytest

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.active_extremes import (
    ActiveStructuralExtremeTracker,
)
from tct_engine.microstructure.bos import (
    BreakDirection,
    BreakOfStructureDetector,
)
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
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
        13,
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


def make_point(
    *,
    side: StructuralPointSide,
    price: float,
) -> EstablishedStructuralPoint:
    candle = make_candle(
        0,
        open_price=price,
        high=price,
        low=price,
        close=price,
    )

    return EstablishedStructuralPoint(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        side=side,
        price=price,
        extreme_candle=candle,
        established_by=candle,
    )


def test_close_above_high_creates_bullish_bos() -> None:
    tracker = ActiveStructuralExtremeTracker()

    tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    detector = BreakOfStructureDetector(
        extreme_tracker=tracker,
    )

    candle = make_candle(
        1,
        open_price=1.1040,
        high=1.1060,
        low=1.1030,
        close=1.1055,
    )

    bos = detector.process_bar(candle)

    assert bos is not None
    assert bos.direction is BreakDirection.BULLISH
    assert bos.broken_extreme.price == 1.1050


def test_wick_above_high_without_close_is_not_bos() -> None:
    tracker = ActiveStructuralExtremeTracker()

    tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    detector = BreakOfStructureDetector(
        extreme_tracker=tracker,
    )

    candle = make_candle(
        1,
        open_price=1.1040,
        high=1.1060,
        low=1.1030,
        close=1.1045,
    )

    assert detector.process_bar(candle) is None


def test_close_below_low_creates_bearish_bos() -> None:
    tracker = ActiveStructuralExtremeTracker()

    tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    detector = BreakOfStructureDetector(
        extreme_tracker=tracker,
    )

    candle = make_candle(
        1,
        open_price=1.0960,
        high=1.0970,
        low=1.0940,
        close=1.0945,
    )

    bos = detector.process_bar(candle)

    assert bos is not None
    assert bos.direction is BreakDirection.BEARISH


def test_close_exactly_on_structure_is_not_bos() -> None:
    tracker = ActiveStructuralExtremeTracker()

    tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    detector = BreakOfStructureDetector(
        extreme_tracker=tracker,
    )

    candle = make_candle(
        1,
        open_price=1.1040,
        high=1.1060,
        low=1.1030,
        close=1.1050,
    )

    assert detector.process_bar(candle) is None


def test_consumed_structure_cannot_generate_second_bos() -> None:
    tracker = ActiveStructuralExtremeTracker()

    tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    detector = BreakOfStructureDetector(
        extreme_tracker=tracker,
    )

    first_break = make_candle(
        1,
        open_price=1.1040,
        high=1.1060,
        low=1.1030,
        close=1.1055,
    )

    second_break = make_candle(
        2,
        open_price=1.1055,
        high=1.1070,
        low=1.1050,
        close=1.1065,
    )

    assert detector.process_bar(first_break) is not None
    assert detector.process_bar(second_break) is None


def test_extended_high_becomes_bos_target() -> None:
    tracker = ActiveStructuralExtremeTracker()

    tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    extension = make_candle(
        1,
        open_price=1.1040,
        high=1.1060,
        low=1.1030,
        close=1.1045,
    )

    tracker.process_bar(
        extension,
        side=StructuralPointSide.HIGH,
    )

    detector = BreakOfStructureDetector(
        extreme_tracker=tracker,
    )

    weak_close = make_candle(
        2,
        open_price=1.1050,
        high=1.1065,
        low=1.1040,
        close=1.1055,
    )

    assert detector.process_bar(weak_close) is None

    true_break = make_candle(
        3,
        open_price=1.1055,
        high=1.1070,
        low=1.1050,
        close=1.1065,
    )

    bos = detector.process_bar(true_break)

    assert bos is not None
    assert bos.broken_extreme.price == 1.1060


def test_open_bar_is_rejected() -> None:
    tracker = ActiveStructuralExtremeTracker()

    detector = BreakOfStructureDetector(
        extreme_tracker=tracker,
    )

    closed = make_candle(
        0,
        open_price=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )

    open_candle = Candle(
        instrument=closed.instrument,
        timeframe=closed.timeframe,
        open_time=closed.open_time,
        close_time=closed.close_time,
        open=closed.open,
        high=closed.high,
        low=closed.low,
        close=closed.close,
        tick_volume=closed.tick_volume,
        is_closed=False,
    )

    with pytest.raises(ValueError, match="closed candle"):
        detector.process_bar(open_candle)
