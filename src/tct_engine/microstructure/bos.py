from dataclasses import dataclass
from enum import Enum, auto

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.active_extremes import (
    ActiveStructuralExtreme,
    ActiveStructuralExtremeTracker,
)
from tct_engine.microstructure.structural_points import StructuralPointSide


class BreakDirection(Enum):
    BULLISH = auto()
    BEARISH = auto()


@dataclass(frozen=True, slots=True)
class BreakOfStructure:
    instrument: str
    timeframe: Timeframe
    direction: BreakDirection
    broken_extreme: ActiveStructuralExtreme
    break_candle: Candle


class BreakOfStructureDetector:
    """Detect close-based breaks of active structural extremes."""

    def __init__(
        self,
        *,
        extreme_tracker: ActiveStructuralExtremeTracker,
    ) -> None:
        self._extreme_tracker = extreme_tracker

        self._consumed: set[tuple[str, Timeframe, StructuralPointSide, float]] = set()

    def process_bar(
        self,
        candle: Candle,
    ) -> BreakOfStructure | None:
        if not candle.is_closed:
            raise ValueError("BOS detection requires a closed candle.")

        bullish = self._check_bullish_break(candle)

        if bullish is not None:
            return bullish

        return self._check_bearish_break(candle)

    def _check_bullish_break(
        self,
        candle: Candle,
    ) -> BreakOfStructure | None:
        extreme = self._extreme_tracker.get(
            instrument=candle.instrument,
            timeframe=candle.timeframe,
            side=StructuralPointSide.HIGH,
        )

        if extreme is None:
            return None

        key = self._key(extreme)

        if key in self._consumed:
            return None

        if candle.close <= extreme.price:
            return None

        self._consumed.add(key)

        return BreakOfStructure(
            instrument=candle.instrument,
            timeframe=candle.timeframe,
            direction=BreakDirection.BULLISH,
            broken_extreme=extreme,
            break_candle=candle,
        )

    def _check_bearish_break(
        self,
        candle: Candle,
    ) -> BreakOfStructure | None:
        extreme = self._extreme_tracker.get(
            instrument=candle.instrument,
            timeframe=candle.timeframe,
            side=StructuralPointSide.LOW,
        )

        if extreme is None:
            return None

        key = self._key(extreme)

        if key in self._consumed:
            return None

        if candle.close >= extreme.price:
            return None

        self._consumed.add(key)

        return BreakOfStructure(
            instrument=candle.instrument,
            timeframe=candle.timeframe,
            direction=BreakDirection.BEARISH,
            broken_extreme=extreme,
            break_candle=candle,
        )

    @staticmethod
    def _key(
        extreme: ActiveStructuralExtreme,
    ) -> tuple[str, Timeframe, StructuralPointSide, float]:
        return (
            extreme.instrument,
            extreme.timeframe,
            extreme.side,
            extreme.price,
        )
