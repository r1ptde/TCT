from dataclasses import dataclass
from enum import Enum, auto

from tct_engine.domain.market_data import Candle


class LegDirection(Enum):
    BULLISH = auto()
    BEARISH = auto()


@dataclass(frozen=True, slots=True)
class StructuralLegDetection:
    direction: LegDirection
    first_candle: Candle
    second_candle: Candle


class StructuralLegDetector:
    """Detect strong two-candle directional structural legs."""

    def __init__(self) -> None:
        self._previous: dict[tuple[str, object], Candle] = {}

    def process_bar(self, candle: Candle) -> StructuralLegDetection | None:
        if not candle.is_closed:
            raise ValueError("Structural leg detection requires a closed candle.")

        key = (candle.instrument, candle.timeframe)
        previous = self._previous.get(key)

        self._previous[key] = candle

        if previous is None:
            return None

        if self._is_bearish(previous) and self._is_bearish(candle) and candle.low < previous.low:
            return StructuralLegDetection(
                direction=LegDirection.BEARISH,
                first_candle=previous,
                second_candle=candle,
            )

        if self._is_bullish(previous) and self._is_bullish(candle) and candle.high > previous.high:
            return StructuralLegDetection(
                direction=LegDirection.BULLISH,
                first_candle=previous,
                second_candle=candle,
            )

        return None

    @staticmethod
    def _is_bullish(candle: Candle) -> bool:
        return candle.close > candle.open

    @staticmethod
    def _is_bearish(candle: Candle) -> bool:
        return candle.close < candle.open
