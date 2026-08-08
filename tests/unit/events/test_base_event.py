from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID

import pytest

from tct_engine.events.base import Event


def test_event_is_immutable() -> None:
    event = Event(
        event_id=UUID("00000000-0000-0000-0000-000000000001"),
        occurred_at=datetime(2026, 8, 7, 8, 0, tzinfo=UTC),
        emitted_at=datetime(2026, 8, 7, 8, 0, tzinfo=UTC),
        source="unit-test",
    )

    with pytest.raises(FrozenInstanceError):
        event.source = "changed"  # type: ignore[misc]


def test_event_supports_causal_links() -> None:
    correlation_id = UUID("00000000-0000-0000-0000-000000000010")
    causation_id = UUID("00000000-0000-0000-0000-000000000011")

    event = Event(
        event_id=UUID("00000000-0000-0000-0000-000000000012"),
        occurred_at=datetime(2026, 8, 7, 8, 0, tzinfo=UTC),
        emitted_at=datetime(2026, 8, 7, 8, 0, tzinfo=UTC),
        source="unit-test",
        correlation_id=correlation_id,
        causation_id=causation_id,
    )

    assert event.correlation_id == correlation_id
    assert event.causation_id == causation_id
