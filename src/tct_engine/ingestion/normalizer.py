from datetime import UTC

from tct_engine.domain.market_data import Tick
from tct_engine.ingestion.models import RawTick


class TickNormalizer:
    """Convert external tick data into the engine's canonical representation."""

    def normalize(self, raw_tick: RawTick) -> Tick:
        timestamp = raw_tick.timestamp

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Tick timestamp must be timezone-aware.")

        return Tick(
            instrument=raw_tick.instrument.strip().upper(),
            timestamp=timestamp.astimezone(UTC),
            bid=float(raw_tick.bid),
            ask=float(raw_tick.ask),
            sequence=raw_tick.sequence,
            source=raw_tick.source,
        )
