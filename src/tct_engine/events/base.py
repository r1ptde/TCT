from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    event_id: UUID
    occurred_at: datetime
    emitted_at: datetime
    source: str
    correlation_id: UUID | None = None
    causation_id: UUID | None = None