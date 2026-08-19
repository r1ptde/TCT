from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.bos_policy import (
    AlwaysM1BosPolicy,
    HierarchyAwareBosPolicy,
)
from tct_engine.microstructure.hierarchy import (
    StructureHierarchy,
    StructureLevel,
    StructureLevelName,
)
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)


def make_point(
    *,
    timeframe: Timeframe,
    price: float,
    index: int,
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
        side=StructuralPointSide.LOW,
        price=price,
        extreme_candle=candle,
        established_by=candle,
    )


def make_level(
    *,
    name: StructureLevelName,
    timeframe: Timeframe,
    price: float,
    index: int,
    obstructed: bool = False,
) -> StructureLevel:
    return StructureLevel(
        name=name,
        point=make_point(
            timeframe=timeframe,
            price=price,
            index=index,
        ),
        timeframe=timeframe,
        obstructed=obstructed,
    )


def test_hierarchy_policy_selects_deepest_unobstructed_level() -> None:
    hierarchy = StructureHierarchy(
        instrument="EURUSD",
        side=StructuralPointSide.LOW,
        levels=(
            make_level(
                name=StructureLevelName.LEVEL_1,
                timeframe=Timeframe.M15,
                price=1.1000,
                index=0,
            ),
            make_level(
                name=StructureLevelName.LEVEL_2,
                timeframe=Timeframe.M5,
                price=1.1020,
                index=1,
            ),
            make_level(
                name=StructureLevelName.LEVEL_3,
                timeframe=Timeframe.M3,
                price=1.1030,
                index=2,
            ),
        ),
    )

    target = HierarchyAwareBosPolicy().select_target(hierarchy)

    assert target is not None
    assert target.name is StructureLevelName.LEVEL_3
    assert target.timeframe is Timeframe.M3


def test_hierarchy_policy_skips_obstructed_level() -> None:
    hierarchy = StructureHierarchy(
        instrument="EURUSD",
        side=StructuralPointSide.LOW,
        levels=(
            make_level(
                name=StructureLevelName.LEVEL_1,
                timeframe=Timeframe.M15,
                price=1.1000,
                index=0,
            ),
            make_level(
                name=StructureLevelName.LEVEL_2,
                timeframe=Timeframe.M5,
                price=1.1020,
                index=1,
            ),
            make_level(
                name=StructureLevelName.LEVEL_3,
                timeframe=Timeframe.M3,
                price=1.1030,
                index=2,
                obstructed=True,
            ),
        ),
    )

    target = HierarchyAwareBosPolicy().select_target(hierarchy)

    assert target is not None
    assert target.name is StructureLevelName.LEVEL_2


def test_always_m1_policy_selects_m1() -> None:
    hierarchy = StructureHierarchy(
        instrument="EURUSD",
        side=StructuralPointSide.LOW,
        levels=(
            make_level(
                name=StructureLevelName.LEVEL_1,
                timeframe=Timeframe.M15,
                price=1.1000,
                index=0,
            ),
            make_level(
                name=StructureLevelName.LEVEL_2,
                timeframe=Timeframe.M3,
                price=1.1020,
                index=1,
            ),
            make_level(
                name=StructureLevelName.LEVEL_3,
                timeframe=Timeframe.M1,
                price=1.1030,
                index=2,
            ),
        ),
    )

    target = AlwaysM1BosPolicy().select_target(hierarchy)

    assert target is not None
    assert target.timeframe is Timeframe.M1


def test_always_m1_policy_returns_none_without_m1() -> None:
    hierarchy = StructureHierarchy(
        instrument="EURUSD",
        side=StructuralPointSide.LOW,
        levels=(
            make_level(
                name=StructureLevelName.LEVEL_1,
                timeframe=Timeframe.M15,
                price=1.1000,
                index=0,
            ),
            make_level(
                name=StructureLevelName.LEVEL_2,
                timeframe=Timeframe.M5,
                price=1.1020,
                index=1,
            ),
            make_level(
                name=StructureLevelName.LEVEL_3,
                timeframe=Timeframe.M3,
                price=1.1030,
                index=2,
            ),
        ),
    )

    target = AlwaysM1BosPolicy().select_target(hierarchy)

    assert target is None
