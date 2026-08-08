from uuid import UUID

import pytest

from tct_engine.engine.identifiers import FixedSequenceIdGenerator


def test_fixed_sequence_id_generator_returns_ids_in_order() -> None:
    first = UUID("00000000-0000-0000-0000-000000000001")
    second = UUID("00000000-0000-0000-0000-000000000002")

    generator = FixedSequenceIdGenerator([first, second])

    assert generator.next_id() == first
    assert generator.next_id() == second


def test_fixed_sequence_id_generator_fails_when_exhausted() -> None:
    generator = FixedSequenceIdGenerator([])

    with pytest.raises(RuntimeError, match="No IDs remaining"):
        generator.next_id()
