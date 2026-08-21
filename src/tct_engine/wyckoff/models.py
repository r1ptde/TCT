from dataclasses import dataclass
from enum import Enum, auto

from tct_engine.domain.enums import Timeframe
from tct_engine.microstructure.bos import BreakOfStructure
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
)
from tct_engine.microstructure.supply_demand import SupplyDemandZone
from tct_engine.wyckoff.range import RangeSide, WyckoffRange
from tct_engine.wyckoff.taps import Tap


class WyckoffModelType(Enum):
    MODEL_1 = auto()
    MODEL_2 = auto()


class Model2TriggerType(Enum):
    SUPPLY_DEMAND = auto()
    LIQUIDITY_SWEEP = auto()


class ModelStatus(Enum):
    CANDIDATE = auto()
    CONFIRMED = auto()
    INVALIDATED = auto()


@dataclass(frozen=True, slots=True)
class LiquidityPoint:
    instrument: str
    timeframe: Timeframe
    price: float
    structural_point: EstablishedStructuralPoint


@dataclass(frozen=True, slots=True)
class Model2Candidate:
    wyckoff_range: WyckoffRange
    tap_2: Tap
    trigger_type: Model2TriggerType
    trigger_price: float
    supply_demand_zone: SupplyDemandZone | None = None
    liquidity_point: LiquidityPoint | None = None


@dataclass(frozen=True, slots=True)
class ConfirmedWyckoffModel:
    model_type: WyckoffModelType
    wyckoff_range: WyckoffRange
    tap_2: Tap
    tap_3: Tap | None
    confirmation_bos: BreakOfStructure | None
    model_2_trigger: Model2TriggerType | None = None


def extreme_section_bounds(
    wyckoff_range: WyckoffRange,
) -> tuple[float, float]:
    range_size = wyckoff_range.high - wyckoff_range.low

    if wyckoff_range.side is RangeSide.ACCUMULATION:
        return (
            wyckoff_range.low,
            wyckoff_range.low + (range_size * 0.25),
        )

    return (
        wyckoff_range.high - (range_size * 0.25),
        wyckoff_range.high,
    )


def price_is_in_extreme_section(
    *,
    wyckoff_range: WyckoffRange,
    price: float,
) -> bool:
    lower, upper = extreme_section_bounds(wyckoff_range)

    return lower <= price <= upper
