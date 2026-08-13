from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.active_extremes import (
    ActiveStructuralExtremeTracker,
)
from tct_engine.microstructure.bos import (
    BreakDirection,
    BreakOfStructure,
)
from tct_engine.microstructure.legs import (
    LegDirection,
    StructuralLegDetection,
)
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)
from tct_engine.microstructure.supply_demand import (
    SupplyDemandSide,
    SupplyDemandStatus,
    SupplyDemandZoneFactory,
    SupplyDemandZoneTracker,
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


def make_bullish_bos(
    tracker: ActiveStructuralExtremeTracker,
) -> BreakOfStructure:
    high = tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.LOW,
            price=1.1000,
        )
    )

    break_candle = make_candle(
        1,
        open_price=1.1040,
        high=1.1070,
        low=1.1030,
        close=1.1060,
    )

    return BreakOfStructure(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        direction=BreakDirection.BULLISH,
        broken_extreme=high,
        break_candle=break_candle,
    )


def test_bullish_bos_creates_demand_zone() -> None:
    extreme_tracker = ActiveStructuralExtremeTracker()

    bos = make_bullish_bos(extreme_tracker)

    factory = SupplyDemandZoneFactory(
        extreme_tracker=extreme_tracker,
    )

    zone = factory.create(bos)

    assert zone is not None
    assert zone.side is SupplyDemandSide.DEMAND
    assert zone.lower_bound == 1.1000
    assert zone.upper_bound == 1.1050
    assert zone.status is SupplyDemandStatus.ACTIVE


def test_wick_into_demand_marks_zone_touched() -> None:
    extreme_tracker = ActiveStructuralExtremeTracker()
    zone = SupplyDemandZoneFactory(
        extreme_tracker=extreme_tracker,
    ).create(make_bullish_bos(extreme_tracker))

    assert zone is not None

    tracker = SupplyDemandZoneTracker()
    tracker.add(zone)

    touch = make_candle(
        2,
        open_price=1.1060,
        high=1.1065,
        low=1.1040,
        close=1.1055,
    )

    tracker.process_bar(touch)

    assert tracker.zones[0].status is SupplyDemandStatus.TOUCHED
    assert tracker.zones[0].touched_by == touch


def test_touch_alone_does_not_mitigate_zone() -> None:
    extreme_tracker = ActiveStructuralExtremeTracker()
    zone = SupplyDemandZoneFactory(
        extreme_tracker=extreme_tracker,
    ).create(make_bullish_bos(extreme_tracker))

    assert zone is not None

    tracker = SupplyDemandZoneTracker()
    tracker.add(zone)

    touch = make_candle(
        2,
        open_price=1.1060,
        high=1.1065,
        low=1.1040,
        close=1.1055,
    )

    tracker.process_bar(touch)

    assert tracker.zones[0].status is SupplyDemandStatus.TOUCHED


def test_valid_bullish_leg_away_mitigates_demand() -> None:
    extreme_tracker = ActiveStructuralExtremeTracker()
    zone = SupplyDemandZoneFactory(
        extreme_tracker=extreme_tracker,
    ).create(make_bullish_bos(extreme_tracker))

    assert zone is not None

    tracker = SupplyDemandZoneTracker()
    tracker.add(zone)

    touch = make_candle(
        2,
        open_price=1.1060,
        high=1.1065,
        low=1.1040,
        close=1.1050,
    )

    tracker.process_bar(touch)

    first = make_candle(
        3,
        open_price=1.1048,
        high=1.1055,
        low=1.1045,
        close=1.1053,
    )

    second = make_candle(
        4,
        open_price=1.1052,
        high=1.1070,
        low=1.1050,
        close=1.1065,
    )

    leg = StructuralLegDetection(
        direction=LegDirection.BULLISH,
        first_candle=first,
        second_candle=second,
    )

    tracker.process_leg(leg)

    assert tracker.zones[0].status is SupplyDemandStatus.MITIGATED
    assert tracker.zones[0].mitigated_by == leg


def test_bullish_leg_that_remains_inside_demand_does_not_mitigate() -> None:
    extreme_tracker = ActiveStructuralExtremeTracker()
    zone = SupplyDemandZoneFactory(
        extreme_tracker=extreme_tracker,
    ).create(make_bullish_bos(extreme_tracker))

    assert zone is not None

    tracker = SupplyDemandZoneTracker()
    tracker.add(zone)

    touch = make_candle(
        2,
        open_price=1.1040,
        high=1.1045,
        low=1.1030,
        close=1.1035,
    )

    tracker.process_bar(touch)

    first = make_candle(
        3,
        open_price=1.1035,
        high=1.1040,
        low=1.1030,
        close=1.1038,
    )

    second = make_candle(
        4,
        open_price=1.1038,
        high=1.1048,
        low=1.1035,
        close=1.1045,
    )

    tracker.process_leg(
        StructuralLegDetection(
            direction=LegDirection.BULLISH,
            first_candle=first,
            second_candle=second,
        )
    )

    assert tracker.zones[0].status is SupplyDemandStatus.TOUCHED


def test_close_below_demand_invalidates_zone() -> None:
    extreme_tracker = ActiveStructuralExtremeTracker()
    zone = SupplyDemandZoneFactory(
        extreme_tracker=extreme_tracker,
    ).create(make_bullish_bos(extreme_tracker))

    assert zone is not None

    tracker = SupplyDemandZoneTracker()
    tracker.add(zone)

    invalidation = make_candle(
        2,
        open_price=1.1010,
        high=1.1020,
        low=1.0990,
        close=1.0995,
    )

    tracker.process_bar(invalidation)

    assert tracker.zones[0].status is SupplyDemandStatus.INVALIDATED
    assert tracker.zones[0].invalidated_by == invalidation


def test_supply_invalidation_is_symmetric() -> None:
    extreme_tracker = ActiveStructuralExtremeTracker()

    low = extreme_tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.LOW,
            price=1.1000,
        )
    )

    extreme_tracker.set_structural_point(
        make_point(
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    bos = BreakOfStructure(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        direction=BreakDirection.BEARISH,
        broken_extreme=low,
        break_candle=make_candle(
            1,
            open_price=1.1010,
            high=1.1020,
            low=1.0980,
            close=1.0990,
        ),
    )

    zone = SupplyDemandZoneFactory(
        extreme_tracker=extreme_tracker,
    ).create(bos)

    assert zone is not None
    assert zone.side is SupplyDemandSide.SUPPLY
    assert zone.lower_bound == 1.1000
    assert zone.upper_bound == 1.1050

    tracker = SupplyDemandZoneTracker()
    tracker.add(zone)

    invalidation = make_candle(
        2,
        open_price=1.1040,
        high=1.1070,
        low=1.1030,
        close=1.1060,
    )

    tracker.process_bar(invalidation)

    assert tracker.zones[0].status is SupplyDemandStatus.INVALIDATED
