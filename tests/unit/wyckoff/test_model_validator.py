from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.active_extremes import (
    ActiveStructuralExtreme,
)
from tct_engine.microstructure.bos import (
    BreakDirection,
    BreakOfStructure,
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
from tct_engine.wyckoff.model_validator import (
    Model2CandidateDetector,
    Model2InteractionValidator,
    ModelResolutionPolicy,
    WyckoffModelValidator,
)
from tct_engine.wyckoff.models import (
    Model2TriggerType,
    WyckoffModelType,
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
    high: float,
    low: float,
    close: float,
) -> Candle:
    open_time = START + timedelta(minutes=index)

    return Candle(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=close,
        high=high,
        low=low,
        close=close,
        tick_volume=10,
        is_closed=True,
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
        high=1.1010,
        low=1.1000,
        close=1.1005,
    )

    return Tap(
        number=2,
        price=1.1000,
        candle=candle,
    )


def make_structural_low(
    *,
    price: float,
) -> EstablishedStructuralPoint:
    candle = make_candle(
        1,
        high=price + 0.0010,
        low=price,
        close=price + 0.0005,
    )

    return EstablishedStructuralPoint(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        side=StructuralPointSide.LOW,
        price=price,
        extreme_candle=candle,
        established_by=candle,
    )


def test_lowest_quarter_is_valid_model_two_extreme_section() -> None:
    detector = Model2CandidateDetector()

    point = make_structural_low(price=1.1020)

    candidate = detector.from_liquidity_point(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        point=point,
    )

    assert candidate is not None
    assert candidate.trigger_type is Model2TriggerType.LIQUIDITY_SWEEP


def test_liquidity_above_lowest_quarter_is_not_model_two_candidate() -> None:
    detector = Model2CandidateDetector()

    point = make_structural_low(price=1.1040)

    candidate = detector.from_liquidity_point(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        point=point,
    )

    assert candidate is None


def make_demand_zone(
    *,
    status: SupplyDemandStatus,
) -> SupplyDemandZone:
    structural_high = make_structural_low(price=1.1020)

    high_point = EstablishedStructuralPoint(
        instrument=structural_high.instrument,
        timeframe=structural_high.timeframe,
        side=StructuralPointSide.HIGH,
        price=1.1025,
        extreme_candle=structural_high.extreme_candle,
        established_by=structural_high.established_by,
    )

    extreme = ActiveStructuralExtreme(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        side=StructuralPointSide.HIGH,
        price=1.1025,
        source_point=high_point,
        updated_by=high_point.extreme_candle,
    )

    bos = BreakOfStructure(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        direction=BreakDirection.BULLISH,
        broken_extreme=extreme,
        break_candle=make_candle(
            2,
            high=1.1040,
            low=1.1010,
            close=1.1030,
        ),
    )

    return SupplyDemandZone(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        side=SupplyDemandSide.DEMAND,
        lower_bound=1.1010,
        upper_bound=1.1020,
        created_by=bos,
        status=status,
    )


def test_active_demand_can_create_model_two_candidate() -> None:
    detector = Model2CandidateDetector()

    candidate = detector.from_supply_demand(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        zone=make_demand_zone(
            status=SupplyDemandStatus.ACTIVE,
        ),
    )

    assert candidate is not None
    assert candidate.trigger_type is Model2TriggerType.SUPPLY_DEMAND


def test_touched_demand_is_rejected_for_model_two_v1() -> None:
    detector = Model2CandidateDetector()

    candidate = detector.from_supply_demand(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        zone=make_demand_zone(
            status=SupplyDemandStatus.TOUCHED,
        ),
    )

    assert candidate is None


def test_mitigated_demand_is_rejected_for_model_two() -> None:
    detector = Model2CandidateDetector()

    candidate = detector.from_supply_demand(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        zone=make_demand_zone(
            status=SupplyDemandStatus.MITIGATED,
        ),
    )

    assert candidate is None


def test_liquidity_point_requires_actual_sweep() -> None:
    detector = Model2CandidateDetector()

    candidate = detector.from_liquidity_point(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        point=make_structural_low(price=1.1020),
    )

    assert candidate is not None

    interaction = Model2InteractionValidator()

    assert interaction.interacted(
        candidate=candidate,
        low=1.1019,
        high=1.1030,
    )


def test_touching_liquidity_price_without_sweep_is_not_enough() -> None:
    detector = Model2CandidateDetector()

    candidate = detector.from_liquidity_point(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        point=make_structural_low(price=1.1020),
    )

    assert candidate is not None

    interaction = Model2InteractionValidator()

    assert not interaction.interacted(
        candidate=candidate,
        low=1.1020,
        high=1.1030,
    )


def make_bullish_bos() -> BreakOfStructure:
    point = make_structural_low(price=1.1030)

    high_point = EstablishedStructuralPoint(
        instrument=point.instrument,
        timeframe=point.timeframe,
        side=StructuralPointSide.HIGH,
        price=1.1030,
        extreme_candle=point.extreme_candle,
        established_by=point.established_by,
    )

    extreme = ActiveStructuralExtreme(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        side=StructuralPointSide.HIGH,
        price=1.1030,
        source_point=high_point,
        updated_by=high_point.extreme_candle,
    )

    return BreakOfStructure(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        direction=BreakDirection.BULLISH,
        broken_extreme=extreme,
        break_candle=make_candle(
            4,
            high=1.1050,
            low=1.1020,
            close=1.1040,
        ),
    )


def test_model_two_requires_correct_bos_direction() -> None:
    candidate = Model2CandidateDetector().from_liquidity_point(
        wyckoff_range=make_range(),
        tap_2=make_tap_2(),
        point=make_structural_low(price=1.1020),
    )

    assert candidate is not None

    model = WyckoffModelValidator.confirm_model_2(
        candidate=candidate,
        bos=make_bullish_bos(),
    )

    assert model is not None
    assert model.model_type is WyckoffModelType.MODEL_2
    assert model.confirmation_bos is not None


def test_model_one_takes_precedence_over_model_two() -> None:
    tap_2 = make_tap_2()

    tap_3 = Tap(
        number=3,
        price=1.0980,
        candle=make_candle(
            5,
            high=1.1000,
            low=1.0980,
            close=1.0995,
        ),
    )

    model_1 = WyckoffModelValidator.confirm_model_1(
        wyckoff_range=make_range(),
        tap_2=tap_2,
        tap_3=tap_3,
    )

    candidate = Model2CandidateDetector().from_liquidity_point(
        wyckoff_range=make_range(),
        tap_2=tap_2,
        point=make_structural_low(price=1.1020),
    )

    assert candidate is not None

    model_2 = WyckoffModelValidator.confirm_model_2(
        candidate=candidate,
        bos=make_bullish_bos(),
    )

    resolved = ModelResolutionPolicy.resolve(
        model_1=model_1,
        model_2=model_2,
    )

    assert resolved is not None
    assert resolved.model_type is WyckoffModelType.MODEL_1
