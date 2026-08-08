from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RawTick:
    instrument: str
    timestamp: datetime
    bid: float
    ask: float
    sequence: int | None = None
    source: str | None = None
