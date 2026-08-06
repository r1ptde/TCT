from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto


class MarketBias(Enum):
    BULLISH = auto()
    BEARISH = auto()
    NEUTRAL = auto()


class RangeStatus(Enum):
    FORMING = auto()
    ACTIVE = auto()
    DEVIATING = auto()
    INVALIDATED = auto()
    COMPLETED = auto()


@dataclass(frozen=True, slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int
    price: float
    is_high: bool
    timestamp: datetime
