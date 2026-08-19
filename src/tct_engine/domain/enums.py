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


class SwingSide(Enum):
    HIGH = auto()
    LOW = auto()


class Direction(Enum):
    BULLISH = auto()
    BEARISH = auto()


class Timeframe(Enum):
    M1 = 60
    M3 = 180
    M5 = 300
    M15 = 900
    M30 = 1800
    M45 = 2700

    @property
    def seconds(self) -> int:
        return self.value
