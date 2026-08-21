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
from tct_engine.wyckoff.models import (
    ConfirmedWyckoffModel,
    LiquidityPoint,
    Model2Candidate,
    Model2TriggerType,
    WyckoffModelType,
    price_is_in_extreme_section,
)
from tct_engine.wyckoff.range import RangeSide, WyckoffRange
from tct_engine.wyckoff.taps import Tap


class Model2CandidateDetector:
    """Identify valid Model 2 POIs after Tap 2."""

    def from_supply_demand(
        self,
        *,
        wyckoff_range: WyckoffRange,
        tap_2: Tap,
        zone: SupplyDemandZone,
    ) -> Model2Candidate | None:
        if zone.status is not SupplyDemandStatus.ACTIVE:
            return None

        expected_side = (
            SupplyDemandSide.DEMAND
            if wyckoff_range.side is RangeSide.ACCUMULATION
            else SupplyDemandSide.SUPPLY
        )

        if zone.side is not expected_side:
            return None

        trigger_price = (
            zone.lower_bound if zone.side is SupplyDemandSide.DEMAND else zone.upper_bound
        )

        if not price_is_in_extreme_section(
            wyckoff_range=wyckoff_range,
            price=trigger_price,
        ):
            return None

        return Model2Candidate(
            wyckoff_range=wyckoff_range,
            tap_2=tap_2,
            trigger_type=Model2TriggerType.SUPPLY_DEMAND,
            trigger_price=trigger_price,
            supply_demand_zone=zone,
        )

    def from_liquidity_point(
        self,
        *,
        wyckoff_range: WyckoffRange,
        tap_2: Tap,
        point: EstablishedStructuralPoint,
    ) -> Model2Candidate | None:
        expected_side = (
            StructuralPointSide.LOW
            if wyckoff_range.side is RangeSide.ACCUMULATION
            else StructuralPointSide.HIGH
        )

        if point.side is not expected_side:
            return None

        if not price_is_in_extreme_section(
            wyckoff_range=wyckoff_range,
            price=point.price,
        ):
            return None

        liquidity = LiquidityPoint(
            instrument=point.instrument,
            timeframe=point.timeframe,
            price=point.price,
            structural_point=point,
        )

        return Model2Candidate(
            wyckoff_range=wyckoff_range,
            tap_2=tap_2,
            trigger_type=Model2TriggerType.LIQUIDITY_SWEEP,
            trigger_price=point.price,
            liquidity_point=liquidity,
        )


class Model2InteractionValidator:
    """Determine whether price has interacted with a Model 2 candidate."""

    def interacted(
        self,
        *,
        candidate: Model2Candidate,
        low: float,
        high: float,
    ) -> bool:
        if candidate.trigger_type is Model2TriggerType.SUPPLY_DEMAND:
            zone = candidate.supply_demand_zone

            if zone is None:
                return False

            return high >= zone.lower_bound and low <= zone.upper_bound

        if candidate.liquidity_point is None:
            return False

        if candidate.wyckoff_range.side is RangeSide.ACCUMULATION:
            return low < candidate.liquidity_point.price

        return high > candidate.liquidity_point.price


class WyckoffModelValidator:
    """Confirm Model 1 and Model 2 setups."""

    @staticmethod
    def confirm_model_1(
        *,
        wyckoff_range: WyckoffRange,
        tap_2: Tap,
        tap_3: Tap,
    ) -> ConfirmedWyckoffModel:
        return ConfirmedWyckoffModel(
            model_type=WyckoffModelType.MODEL_1,
            wyckoff_range=wyckoff_range,
            tap_2=tap_2,
            tap_3=tap_3,
            confirmation_bos=None,
        )

    @staticmethod
    def confirm_model_2(
        *,
        candidate: Model2Candidate,
        bos: BreakOfStructure,
    ) -> ConfirmedWyckoffModel | None:
        expected_direction = (
            BreakDirection.BULLISH
            if candidate.wyckoff_range.side is RangeSide.ACCUMULATION
            else BreakDirection.BEARISH
        )

        if bos.direction is not expected_direction:
            return None

        return ConfirmedWyckoffModel(
            model_type=WyckoffModelType.MODEL_2,
            wyckoff_range=candidate.wyckoff_range,
            tap_2=candidate.tap_2,
            tap_3=None,
            confirmation_bos=bos,
            model_2_trigger=candidate.trigger_type,
        )


class ModelResolutionPolicy:
    """Resolve overlapping model classifications."""

    @staticmethod
    def resolve(
        *,
        model_1: ConfirmedWyckoffModel | None,
        model_2: ConfirmedWyckoffModel | None,
    ) -> ConfirmedWyckoffModel | None:
        if model_1 is not None:
            return model_1

        return model_2
