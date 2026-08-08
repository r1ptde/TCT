from tct_engine.domain.enums import Timeframe
from tct_engine.engine.event_bus import EventBus
from tct_engine.engine.identifiers import IdGenerator
from tct_engine.events.market_data import (
    BarClosed,
    BarOpened,
    BarUpdated,
    TickValidated,
)
from tct_engine.infrastructure.clock import Clock
from tct_engine.ingestion.aggregator import BarAggregator


class BarAggregationProcessor:
    """Consume validated ticks and emit bar lifecycle events."""

    def __init__(
        self,
        *,
        event_bus: EventBus,
        clock: Clock,
        id_generator: IdGenerator,
        timeframes: tuple[Timeframe, ...],
    ) -> None:
        self._event_bus = event_bus
        self._clock = clock
        self._id_generator = id_generator
        self._aggregators = {timeframe: BarAggregator(timeframe) for timeframe in timeframes}

    async def on_tick_validated(self, event: TickValidated) -> None:
        for aggregator in self._aggregators.values():
            closed, current = aggregator.process_tick(event.tick)

            if closed is not None:
                await self._event_bus.publish(
                    BarClosed(
                        event_id=self._id_generator.next_id(),
                        occurred_at=closed.close_time,
                        emitted_at=self._clock.now(),
                        source="bar-aggregation",
                        correlation_id=event.correlation_id,
                        causation_id=event.event_id,
                        candle=closed,
                    )
                )

                await self._event_bus.publish(
                    BarOpened(
                        event_id=self._id_generator.next_id(),
                        occurred_at=current.open_time,
                        emitted_at=self._clock.now(),
                        source="bar-aggregation",
                        correlation_id=event.correlation_id,
                        causation_id=event.event_id,
                        candle=current,
                    )
                )
                continue

            if current.tick_volume == 1:
                await self._event_bus.publish(
                    BarOpened(
                        event_id=self._id_generator.next_id(),
                        occurred_at=event.tick.timestamp,
                        emitted_at=self._clock.now(),
                        source="bar-aggregation",
                        correlation_id=event.correlation_id,
                        causation_id=event.event_id,
                        candle=current,
                    )
                )
            else:
                await self._event_bus.publish(
                    BarUpdated(
                        event_id=self._id_generator.next_id(),
                        occurred_at=event.tick.timestamp,
                        emitted_at=self._clock.now(),
                        source="bar-aggregation",
                        correlation_id=event.correlation_id,
                        causation_id=event.event_id,
                        candle=current,
                    )
                )
