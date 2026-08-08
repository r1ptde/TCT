from datetime import UTC, datetime, timedelta

from tct_engine.domain.market_data import Tick
from tct_engine.ingestion.validation import (
    TickRejectionReason,
    TickValidator,
)


def make_tick(
    *,
    timestamp: datetime | None = None,
    bid: float = 1.1500,
    ask: float = 1.1502,
    sequence: int | None = None,
) -> Tick:
    return Tick(
        instrument="EURUSD",
        timestamp=timestamp or datetime(2026, 8, 8, 8, 0, tzinfo=UTC),
        bid=bid,
        ask=ask,
        sequence=sequence,
        source="test-feed",
    )


def test_valid_tick_is_accepted() -> None:
    result = TickValidator().validate(make_tick())

    assert result.is_valid
    assert result.reason is None


def test_non_positive_bid_is_rejected() -> None:
    result = TickValidator().validate(make_tick(bid=0.0))

    assert result.reason is TickRejectionReason.NON_POSITIVE_BID


def test_non_positive_ask_is_rejected() -> None:
    result = TickValidator().validate(make_tick(ask=0.0))

    assert result.reason is TickRejectionReason.NON_POSITIVE_ASK


def test_crossed_market_is_rejected() -> None:
    result = TickValidator().validate(
        make_tick(
            bid=1.1503,
            ask=1.1502,
        )
    )

    assert result.reason is TickRejectionReason.CROSSED_MARKET


def test_duplicate_tick_is_rejected() -> None:
    validator = TickValidator()
    tick = make_tick(sequence=1)

    assert validator.validate(tick).is_valid

    result = validator.validate(tick)

    assert result.reason is TickRejectionReason.DUPLICATE_TICK


def test_out_of_order_timestamp_is_rejected() -> None:
    validator = TickValidator()

    current = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)

    assert validator.validate(make_tick(timestamp=current, sequence=10)).is_valid

    result = validator.validate(
        make_tick(
            timestamp=current - timedelta(milliseconds=1),
            sequence=11,
        )
    )

    assert result.reason is TickRejectionReason.OUT_OF_ORDER_TIMESTAMP


def test_non_increasing_sequence_is_rejected() -> None:
    validator = TickValidator()

    timestamp = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)

    assert validator.validate(make_tick(timestamp=timestamp, sequence=10)).is_valid

    result = validator.validate(
        make_tick(
            timestamp=timestamp + timedelta(milliseconds=1),
            sequence=9,
        )
    )

    assert result.reason is TickRejectionReason.NON_INCREASING_SEQUENCE


def test_equal_timestamps_are_allowed_for_different_ticks() -> None:
    validator = TickValidator()

    timestamp = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)

    first = make_tick(
        timestamp=timestamp,
        bid=1.1500,
        ask=1.1502,
        sequence=1,
    )

    second = make_tick(
        timestamp=timestamp,
        bid=1.1501,
        ask=1.1503,
        sequence=2,
    )

    assert validator.validate(first).is_valid
    assert validator.validate(second).is_valid
