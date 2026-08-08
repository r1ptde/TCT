from tct_engine.engine.event_bus import EventBus
from tct_engine.engine.identifiers import IdGenerator
from tct_engine.events.market_data import (
    TickReceived,
    TickRejected,
    TickValidated,
)
from tct_engine.infrastructure.clock import Clock
from tct_engine.ingestion.models import RawTick
from tct_engine.ingestion.normalizer import TickNormalizer
from tct_engine.ingestion.validation import TickValidator


class TickIngestionPipeline:
    """Normalize, validate, and publish canonical tick events."""

    def __init__(
        self,
        *,
        event_bus: EventBus,
        clock: Clock,
        id_generator: IdGenerator,
        normalizer: TickNormalizer | None = None,
        validator: TickValidator | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._clock = clock
        self._id_generator = id_generator
        self._normalizer = normalizer or TickNormalizer()
        self._validator = validator or TickValidator()

    async def process(self, raw_tick: RawTick) -> None:
        tick = self._normalizer.normalize(raw_tick)

        received_event = TickReceived(
            event_id=self._id_generator.next_id(),
            occurred_at=tick.timestamp,
            emitted_at=self._clock.now(),
            source="tick-ingestion",
            tick=tick,
        )

        await self._event_bus.publish(received_event)

        validation = self._validator.validate(tick)

        if validation.is_valid:
            validated_event = TickValidated(
                event_id=self._id_generator.next_id(),
                occurred_at=tick.timestamp,
                emitted_at=self._clock.now(),
                source="tick-ingestion",
                correlation_id=received_event.event_id,
                causation_id=received_event.event_id,
                tick=tick,
            )

            await self._event_bus.publish(validated_event)
            return

        if validation.reason is None:
            raise RuntimeError("Rejected tick is missing a rejection reason.")

        rejected_event = TickRejected(
            event_id=self._id_generator.next_id(),
            occurred_at=tick.timestamp,
            emitted_at=self._clock.now(),
            source="tick-ingestion",
            correlation_id=received_event.event_id,
            causation_id=received_event.event_id,
            tick=tick,
            reason=validation.reason,
        )

        await self._event_bus.publish(rejected_event)
