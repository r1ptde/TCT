from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from tct_engine.domain.enums import SwingSide, Timeframe


@dataclass(frozen=True, slots=True)
class SwingPoint:
    swing_id: UUID
    instrument: str
    timeframe: Timeframe
    timestamp: datetime
    price: float
    side: SwingSide
    confirmed_at: datetime
