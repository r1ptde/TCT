from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.hierarchy import (
    StructureHierarchyBuilder,
    StructureLevelName,
)
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)
from tct_engine.microstructure.supply_demand import (
    SupplyDemandSide,
    SupplyDemandStatus,
    SupplyDemandZone,
)


def make_point(
    *,
    timeframe: Timeframe,
    side: StructuralPointSide,
    price: float,
    index: int = 0,
) -> EstablishedStructuralPoint:
    open_time = datetime(
        2026,
        8,
        19,
        8,
        0,
        tzinfo=UTC,
    ) + timedelta(minutes=index)

    candle = Candle(
        instrument="EURUSD",
        timeframe=timeframe,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=price,
        high=price,
        low=price,
        close=price,
        tick_volume=10,
        is_closed=True,
    )

    return EstablishedStructuralPoint(
        instrument="EURUSD",
        timeframe=timeframe,
        side=side,
        price=price,
        extreme_candle=candle,
        established_by=candle,
    )


def test_same_price_across_timeframes_is_one_level() -> None:
    builder = StructureHierarchyBuilder()

    hierarchy = builder.build(
        instrument="EURUSD",
        side=StructuralPointSide.LOW,
        points_by_timeframe={
            Timeframe.M15: make_point(
                timeframe=Timeframe.M15,
                side=StructuralPointSide.LOW,
                price=1.1000,
            ),
            Timeframe.M5: make_point(
                timeframe=Timeframe.M5,
                side=StructuralPointSide.LOW,
                price=1.1000,
            ),
            Timeframe.M3: make_point(
                timeframe=Timeframe.M3,
                side=StructuralPointSide.LOW,
                price=1.1020,
            ),
            Timeframe.M1: make_point(
                timeframe=Timeframe.M1,
                side=StructuralPointSide.LOW,
                price=1.1030,
            ),
        },
    )

    assert len(hierarchy.levels) == 3

    assert hierarchy.levels[0].name is StructureLevelName.LEVEL_1
    assert hierarchy.levels[0].timeframe is Timeframe.M15
    assert hierarchy.levels[0].point.price == 1.1000

    assert hierarchy.levels[1].name is StructureLevelName.LEVEL_2
    assert hierarchy.levels[1].timeframe is Timeframe.M3

    assert hierarchy.levels[2].name is StructureLevelName.LEVEL_3
    assert hierarchy.levels[2].timeframe is Timeframe.M1


def test_hierarchy_never_creates_level_four() -> None:
    builder = StructureHierarchyBuilder()

    hierarchy = builder.build(
        instrument="EURUSD",
        side=StructuralPointSide.LOW,
        points_by_timeframe={
            Timeframe.M15: make_point(
                timeframe=Timeframe.M15,
                side=StructuralPointSide.LOW,
                price=1.1000,
            ),
            Timeframe.M5: make_point(
                timeframe=Timeframe.M5,
                side=StructuralPointSide.LOW,
                price=1.1010,
            ),
            Timeframe.M3: make_point(
                timeframe=Timeframe.M3,
                side=StructuralPointSide.LOW,
                price=1.1020,
            ),
            Timeframe.M1: make_point(
                timeframe=Timeframe.M1,
                side=StructuralPointSide.LOW,
                price=1.1030,
            ),
        },
    )

    assert len(hierarchy.levels) == 3
    assert hierarchy.levels[-1].timeframe is Timeframe.M3


def make_bos_for_zone(
    *,
    side: SupplyDemandSide,
    lower_bound: float,
    upper_bound: float,
):
    from tct_engine.microstructure.active_extremes import (
        ActiveStructuralExtreme,
    )
    from tct_engine.microstructure.bos import (
        BreakDirection,
        BreakOfStructure,
    )

    if side is SupplyDemandSide.DEMAND:
        structural_side = StructuralPointSide.HIGH
        direction = BreakDirection.BULLISH
        broken_price = upper_bound
        close = upper_bound + 0.0010
    else:
        structural_side = StructuralPointSide.LOW
        direction = BreakDirection.BEARISH
        broken_price = lower_bound
        close = lower_bound - 0.0010

    point = make_point(
        timeframe=Timeframe.M5,
        side=structural_side,
        price=broken_price,
    )

    extreme = ActiveStructuralExtreme(
        instrument="EURUSD",
        timeframe=Timeframe.M5,
        side=structural_side,
        price=broken_price,
        source_point=point,
        updated_by=point.extreme_candle,
    )

    break_candle = Candle(
        instrument="EURUSD",
        timeframe=Timeframe.M5,
        open_time=point.extreme_candle.open_time,
        close_time=point.extreme_candle.close_time,
        open=broken_price,
        high=max(broken_price, close),
        low=min(broken_price, close),
        close=close,
        tick_volume=10,
        is_closed=True,
    )

    return BreakOfStructure(
        instrument="EURUSD",
        timeframe=Timeframe.M5,
        direction=direction,
        broken_extreme=extreme,
        break_candle=break_candle,
    )


def make_zone(
    *,
    side: SupplyDemandSide,
    lower_bound: float,
    upper_bound: float,
    status: SupplyDemandStatus,
) -> SupplyDemandZone:
    return SupplyDemandZone(
        instrument="EURUSD",
        timeframe=Timeframe.M5,
        side=side,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        created_by=make_bos_for_zone(
            side=side,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        ),
        status=status,
    )


def test_unmitigated_demand_obstructs_lower_level() -> None:
    builder = StructureHierarchyBuilder()

    demand = make_zone(
        side=SupplyDemandSide.DEMAND,
        lower_bound=1.1010,
        upper_bound=1.1020,
        status=SupplyDemandStatus.ACTIVE,
    )

    hierarchy = builder.build(
        instrument="EURUSD",
        side=StructuralPointSide.LOW,
        points_by_timeframe={
            Timeframe.M15: make_point(
                timeframe=Timeframe.M15,
                side=StructuralPointSide.LOW,
                price=1.1000,
            ),
            Timeframe.M5: make_point(
                timeframe=Timeframe.M5,
                side=StructuralPointSide.LOW,
                price=1.1030,
            ),
        },
        zones=(demand,),
    )

    assert hierarchy.level_1 is not None
    assert hierarchy.level_2 is not None

    assert hierarchy.level_1.obstructed is False
    assert hierarchy.level_2.obstructed is True


def test_touched_demand_still_obstructs_lower_level() -> None:
    builder = StructureHierarchyBuilder()

    demand = make_zone(
        side=SupplyDemandSide.DEMAND,
        lower_bound=1.1010,
        upper_bound=1.1020,
        status=SupplyDemandStatus.TOUCHED,
    )

    hierarchy = builder.build(
        instrument="EURUSD",
        side=StructuralPointSide.LOW,
        points_by_timeframe={
            Timeframe.M15: make_point(
                timeframe=Timeframe.M15,
                side=StructuralPointSide.LOW,
                price=1.1000,
            ),
            Timeframe.M5: make_point(
                timeframe=Timeframe.M5,
                side=StructuralPointSide.LOW,
                price=1.1030,
            ),
        },
        zones=(demand,),
    )

    assert hierarchy.level_2 is not None
    assert hierarchy.level_2.obstructed is True


def test_mitigated_demand_does_not_obstruct_lower_level() -> None:
    builder = StructureHierarchyBuilder()

    demand = make_zone(
        side=SupplyDemandSide.DEMAND,
        lower_bound=1.1010,
        upper_bound=1.1020,
        status=SupplyDemandStatus.MITIGATED,
    )

    hierarchy = builder.build(
        instrument="EURUSD",
        side=StructuralPointSide.LOW,
        points_by_timeframe={
            Timeframe.M15: make_point(
                timeframe=Timeframe.M15,
                side=StructuralPointSide.LOW,
                price=1.1000,
            ),
            Timeframe.M5: make_point(
                timeframe=Timeframe.M5,
                side=StructuralPointSide.LOW,
                price=1.1030,
            ),
        },
        zones=(demand,),
    )

    assert hierarchy.level_2 is not None
    assert hierarchy.level_2.obstructed is False


def test_unmitigated_supply_obstructs_bearish_lower_level() -> None:
    builder = StructureHierarchyBuilder()

    supply = make_zone(
        side=SupplyDemandSide.SUPPLY,
        lower_bound=1.1080,
        upper_bound=1.1090,
        status=SupplyDemandStatus.ACTIVE,
    )

    hierarchy = builder.build(
        instrument="EURUSD",
        side=StructuralPointSide.HIGH,
        points_by_timeframe={
            Timeframe.M15: make_point(
                timeframe=Timeframe.M15,
                side=StructuralPointSide.HIGH,
                price=1.1100,
            ),
            Timeframe.M5: make_point(
                timeframe=Timeframe.M5,
                side=StructuralPointSide.HIGH,
                price=1.1070,
            ),
        },
        zones=(supply,),
    )

    assert hierarchy.level_2 is not None
    assert hierarchy.level_2.obstructed is True
