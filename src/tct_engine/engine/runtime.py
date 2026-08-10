from dataclasses import dataclass

from tct_engine.domain.enums import Timeframe
from tct_engine.engine.event_bus import EventBus
from tct_engine.engine.identifiers import IdGenerator
from tct_engine.events.market_data import TickValidated
from tct_engine.infrastructure.clock import Clock
from tct_engine.ingestion.bar_processor import BarAggregationProcessor
from tct_engine.ingestion.pipeline import TickIngestionPipeline


@dataclass(slots=True)
class MarketDataRuntime:
    event_bus: EventBus
    ingestion_pipeline: TickIngestionPipeline
    bar_processor: BarAggregationProcessor


def build_market_data_runtime(
    *,
    clock: Clock,
    id_generator: IdGenerator,
    timeframes: tuple[Timeframe, ...] = (
        Timeframe.M1,
        Timeframe.M3,
        Timeframe.M5,
        Timeframe.M15,
    ),
) -> MarketDataRuntime:
    event_bus = EventBus()

    ingestion_pipeline = TickIngestionPipeline(
        event_bus=event_bus,
        clock=clock,
        id_generator=id_generator,
    )

    bar_processor = BarAggregationProcessor(
        event_bus=event_bus,
        clock=clock,
        id_generator=id_generator,
        timeframes=timeframes,
    )

    event_bus.subscribe(
        TickValidated,
        bar_processor.on_tick_validated,
    )

    return MarketDataRuntime(
        event_bus=event_bus,
        ingestion_pipeline=ingestion_pipeline,
        bar_processor=bar_processor,
    )
