from dataclasses import dataclass
from datetime import datetime

from tct_engine.domain.enums import Timeframe


@dataclass(frozen=True, slots=True)
class Tick:
    instrument: str
    timestamp: datetime
    bid: float
    ask: float
    sequence: int | None = None
    source: str | None = None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return self.ask - self.bid


@dataclass(frozen=True, slots=True)
class Candle:
    instrument: str
    timeframe: Timeframe
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    is_closed: bool
