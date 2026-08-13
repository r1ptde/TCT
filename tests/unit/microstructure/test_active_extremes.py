from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.active_extremes import (
    ActiveStructuralExtremeTracker,
)
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)


def make_candle(
    index: int,
    *,
    high: float,
    low: float,
) -> Candle:
    open_time = datetime(
        2026,
        8,
        13,
        8,
        0,
        tzinfo=UTC,
    ) + timedelta(minutes=index)

    midpoint = (high + low) / 2

    return Candle(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=midpoint,
        high=high,
        low=low,
        close=midpoint,
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
        high=price,
        low=price,
    )

    return EstablishedStructuralPoint(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        side=side,
        price=price,
        extreme_candle=candle,
        established_by=candle,
    )


def test_structural_high_can_extend_by_wick() -> None:
    tracker = ActiveStructuralExtremeTracker()

    point = make_point(
        side=StructuralPointSide.HIGH,
        price=1.1050,
    )

    tracker.set_structural_point(point)

    candle = make_candle(
        1,
        high=1.1060,
        low=1.1030,
    )

    active = tracker.process_bar(
        candle,
        side=StructuralPointSide.HIGH,
    )

    assert active is not None
    assert active.price == 1.1060
    assert active.source_point == point
    assert active.updated_by == candle


def test_structural_low_can_extend_by_wick() -> None:
    tracker = ActiveStructuralExtremeTracker()

    point = make_point(
        side=StructuralPointSide.LOW,
        price=1.0950,
    )

    tracker.set_structural_point(point)

    candle = make_candle(
        1,
        high=1.0970,
        low=1.0940,
    )

    active = tracker.process_bar(
        candle,
        side=StructuralPointSide.LOW,
    )

    assert active is not None
    assert active.price == 1.0940


def test_smaller_high_does_not_replace_active_high() -> None:
    tracker = ActiveStructuralExtremeTracker()

    tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    candle = make_candle(
        1,
        high=1.1040,
        low=1.1020,
    )

    active = tracker.process_bar(
        candle,
        side=StructuralPointSide.HIGH,
    )

    assert active is not None
    assert active.price == 1.1050


def test_higher_low_does_not_replace_active_low() -> None:
    tracker = ActiveStructuralExtremeTracker()

    tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    candle = make_candle(
        1,
        high=1.0980,
        low=1.0960,
    )

    active = tracker.process_bar(
        candle,
        side=StructuralPointSide.LOW,
    )

    assert active is not None
    assert active.price == 1.0950


def test_new_structural_point_replaces_old_active_extreme() -> None:
    tracker = ActiveStructuralExtremeTracker()

    old_point = make_point(
        side=StructuralPointSide.HIGH,
        price=1.1050,
    )

    tracker.set_structural_point(old_point)

    extension = make_candle(
        1,
        high=1.1060,
        low=1.1030,
    )

    tracker.process_bar(
        extension,
        side=StructuralPointSide.HIGH,
    )

    new_point = make_point(
        side=StructuralPointSide.HIGH,
        price=1.1100,
    )

    active = tracker.set_structural_point(new_point)

    assert active.price == 1.1100
    assert active.source_point == new_point
