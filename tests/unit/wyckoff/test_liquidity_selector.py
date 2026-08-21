from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.market_structure import (
    StructureClassification,
)
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)
from tct_engine.wyckoff.liquidity_selector import (
    ClassifiedStructuralPoint,
    LiquidityPointStateValidator,
    LiquiditySelectionPolicy,
    Model2LiquiditySelector,
)
from tct_engine.wyckoff.range import (
    RangeSide,
    RangeStatus,
    WyckoffRange,
)
from tct_engine.wyckoff.taps import Tap

START = datetime(2026, 8, 21, 8, 0, tzinfo=UTC)


def make_candle(
    index: int,
    *,
    price: float,
) -> Candle:
    open_time = START + timedelta(minutes=index)

    return Candle(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=price,
        high=price + 0.0010,
        low=price,
        close=price + 0.0005,
        tick_volume=10,
        is_closed=True,
    )


def make_point(
    index: int,
    *,
    price: float,
    side: StructuralPointSide = StructuralPointSide.LOW,
) -> EstablishedStructuralPoint:
    candle = make_candle(
        index,
        price=price,
    )

    return EstablishedStructuralPoint(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        side=side,
        price=price,
        extreme_candle=candle,
        established_by=candle,
    )


def make_range() -> WyckoffRange:
    return WyckoffRange(
        instrument="EURUSD",
        timeframe=Timeframe.M15,
        side=RangeSide.ACCUMULATION,
        high=1.1100,
        low=1.1000,
        tap_count=2,
        status=RangeStatus.ACTIVE,
    )


def make_tap_2() -> Tap:
    candle = make_candle(
        0,
        price=1.1000,
    )

    return Tap(
        number=2,
        price=1.1000,
        candle=candle,
    )


def test_first_valid_policy_selects_first_higher_low() -> None:
    selector = Model2LiquiditySelector()

    first = make_point(
        1,
        price=1.1010,
    )

    second = make_point(
        4,
        price=1.1020,
    )

    selected = selector.select(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        points=(
            ClassifiedStructuralPoint(
                point=first,
                classification=StructureClassification.HL,
            ),
            ClassifiedStructuralPoint(
                point=second,
                classification=StructureClassification.HL,
            ),
        ),
        policy=LiquiditySelectionPolicy.FIRST_VALID,
    )

    assert selected is not None
    assert selected.price == 1.1010


def test_skip_adjacent_policy_uses_next_higher_low() -> None:
    selector = Model2LiquiditySelector()

    adjacent = make_point(
        1,
        price=1.1010,
    )

    second = make_point(
        4,
        price=1.1020,
    )

    selected = selector.select(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        points=(
            ClassifiedStructuralPoint(
                point=adjacent,
                classification=StructureClassification.HL,
            ),
            ClassifiedStructuralPoint(
                point=second,
                classification=StructureClassification.HL,
            ),
        ),
        policy=LiquiditySelectionPolicy.SKIP_ADJACENT,
    )

    assert selected is not None
    assert selected.price == 1.1020


def test_non_adjacent_first_higher_low_is_kept() -> None:
    selector = Model2LiquiditySelector()

    first = make_point(
        3,
        price=1.1015,
    )

    second = make_point(
        5,
        price=1.1025,
    )

    selected = selector.select(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        points=(
            ClassifiedStructuralPoint(
                point=first,
                classification=StructureClassification.HL,
            ),
            ClassifiedStructuralPoint(
                point=second,
                classification=StructureClassification.HL,
            ),
        ),
    )

    assert selected is not None
    assert selected.price == 1.1015


def test_only_higher_lows_are_candidates_for_accumulation() -> None:
    selector = Model2LiquiditySelector()

    point = make_point(
        3,
        price=1.1020,
    )

    selected = selector.select(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        points=(
            ClassifiedStructuralPoint(
                point=point,
                classification=StructureClassification.LL,
            ),
        ),
    )

    assert selected is None


def test_unswept_liquidity_remains_valid() -> None:
    liquidity = Model2LiquiditySelector().select(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        points=(
            ClassifiedStructuralPoint(
                point=make_point(
                    3,
                    price=1.1020,
                ),
                classification=StructureClassification.HL,
            ),
        ),
    )

    assert liquidity is not None

    later_low = make_point(
        6,
        price=1.1030,
    )

    assert LiquidityPointStateValidator.remains_unswept(
        wyckoff_range=make_range(),
        liquidity_point=liquidity,
        subsequent_points=(later_low,),
    )


def test_lower_price_consumes_liquidity() -> None:
    liquidity = Model2LiquiditySelector().select(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        points=(
            ClassifiedStructuralPoint(
                point=make_point(
                    3,
                    price=1.1020,
                ),
                classification=StructureClassification.HL,
            ),
        ),
    )

    assert liquidity is not None

    lower_point = make_point(
        6,
        price=1.1015,
    )

    assert not LiquidityPointStateValidator.remains_unswept(
        wyckoff_range=make_range(),
        liquidity_point=liquidity,
        subsequent_points=(lower_point,),
    )
