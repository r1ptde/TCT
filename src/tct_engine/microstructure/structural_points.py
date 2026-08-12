from dataclasses import dataclass
from enum import Enum, auto

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.legs import (
    LegDirection,
    StructuralLegDetection,
    StructuralLegDetector,
)


class StructuralPointSide(Enum):
    HIGH = auto()
    LOW = auto()


class StructureState(Enum):
    UNINITIALIZED = auto()
    SEEKING_LOW = auto()
    SEEKING_HIGH = auto()


@dataclass(frozen=True, slots=True)
class EstablishedStructuralPoint:
    instrument: str
    timeframe: Timeframe
    side: StructuralPointSide
    price: float
    extreme_candle: Candle
    established_by: Candle


class StructuralPointDetector:
    """Establish alternating structural highs and lows from valid legs."""

    def __init__(
        self,
        *,
        leg_detector: StructuralLegDetector | None = None,
    ) -> None:
        self._leg_detector = leg_detector or StructuralLegDetector()

        self._states: dict[
            tuple[str, Timeframe],
            StructureState,
        ] = {}

        self._initiating_extreme: dict[
            tuple[str, Timeframe],
            float,
        ] = {}

        self._candidate_extreme: dict[
            tuple[str, Timeframe],
            tuple[float, Candle],
        ] = {}

        self._opposite_leg_seen: dict[
            tuple[str, Timeframe],
            bool,
        ] = {}

    def process_bar(
        self,
        candle: Candle,
    ) -> EstablishedStructuralPoint | None:
        if not candle.is_closed:
            raise ValueError("Structural point detection requires a closed candle.")

        key = (candle.instrument, candle.timeframe)

        detection = self._leg_detector.process_bar(candle)

        state = self._states.get(
            key,
            StructureState.UNINITIALIZED,
        )

        if state is StructureState.UNINITIALIZED:
            self._initialize_from_leg(
                key=key,
                detection=detection,
            )
            return None

        self._update_candidate(
            key=key,
            state=state,
            candle=candle,
        )

        if state is StructureState.SEEKING_LOW:
            return self._process_seeking_low(
                key=key,
                candle=candle,
                detection=detection,
            )

        return self._process_seeking_high(
            key=key,
            candle=candle,
            detection=detection,
        )

    def _initialize_from_leg(
        self,
        *,
        key: tuple[str, Timeframe],
        detection: StructuralLegDetection | None,
    ) -> None:
        if detection is None:
            return

        if detection.direction is LegDirection.BEARISH:
            self._states[key] = StructureState.SEEKING_LOW

            self._initiating_extreme[key] = max(
                detection.first_candle.high,
                detection.second_candle.high,
            )

            self._candidate_extreme[key] = self._lowest_candle(
                detection.first_candle,
                detection.second_candle,
            )

            self._opposite_leg_seen[key] = False
            return

        self._states[key] = StructureState.SEEKING_HIGH

        self._initiating_extreme[key] = min(
            detection.first_candle.low,
            detection.second_candle.low,
        )

        self._candidate_extreme[key] = self._highest_candle(
            detection.first_candle,
            detection.second_candle,
        )

        self._opposite_leg_seen[key] = False

    def _update_candidate(
        self,
        *,
        key: tuple[str, Timeframe],
        state: StructureState,
        candle: Candle,
    ) -> None:
        price, _ = self._candidate_extreme[key]

        if state is StructureState.SEEKING_LOW and candle.low < price:
            self._candidate_extreme[key] = (
                candle.low,
                candle,
            )

        elif state is StructureState.SEEKING_HIGH and candle.high > price:
            self._candidate_extreme[key] = (
                candle.high,
                candle,
            )

    def _process_seeking_low(
        self,
        *,
        key: tuple[str, Timeframe],
        candle: Candle,
        detection: StructuralLegDetection | None,
    ) -> EstablishedStructuralPoint | None:
        if detection is not None and detection.direction is LegDirection.BULLISH:
            self._opposite_leg_seen[key] = True

        if not self._opposite_leg_seen[key]:
            return None

        initiating_high = self._initiating_extreme[key]

        if candle.high < initiating_high:
            return None

        low_price, low_candle = self._candidate_extreme[key]

        point = EstablishedStructuralPoint(
            instrument=candle.instrument,
            timeframe=candle.timeframe,
            side=StructuralPointSide.LOW,
            price=low_price,
            extreme_candle=low_candle,
            established_by=candle,
        )

        self._states[key] = StructureState.SEEKING_HIGH
        self._initiating_extreme[key] = low_price
        self._candidate_extreme[key] = (
            candle.high,
            candle,
        )
        self._opposite_leg_seen[key] = False

        return point

    def _process_seeking_high(
        self,
        *,
        key: tuple[str, Timeframe],
        candle: Candle,
        detection: StructuralLegDetection | None,
    ) -> EstablishedStructuralPoint | None:
        if detection is not None and detection.direction is LegDirection.BEARISH:
            self._opposite_leg_seen[key] = True

        if not self._opposite_leg_seen[key]:
            return None

        initiating_low = self._initiating_extreme[key]

        if candle.low > initiating_low:
            return None

        high_price, high_candle = self._candidate_extreme[key]

        point = EstablishedStructuralPoint(
            instrument=candle.instrument,
            timeframe=candle.timeframe,
            side=StructuralPointSide.HIGH,
            price=high_price,
            extreme_candle=high_candle,
            established_by=candle,
        )

        self._states[key] = StructureState.SEEKING_LOW
        self._initiating_extreme[key] = high_price
        self._candidate_extreme[key] = (
            candle.low,
            candle,
        )
        self._opposite_leg_seen[key] = False

        return point

    @staticmethod
    def _lowest_candle(
        first: Candle,
        second: Candle,
    ) -> tuple[float, Candle]:
        if first.low <= second.low:
            return first.low, first

        return second.low, second

    @staticmethod
    def _highest_candle(
        first: Candle,
        second: Candle,
    ) -> tuple[float, Candle]:
        if first.high >= second.high:
            return first.high, first

        return second.high, second
