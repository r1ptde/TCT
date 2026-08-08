from typing import Protocol
from uuid import UUID, uuid4


class IdGenerator(Protocol):
    def next_id(self) -> UUID: ...


class RandomIdGenerator:
    def next_id(self) -> UUID:
        return uuid4()


class FixedSequenceIdGenerator:
    def __init__(self, ids: list[UUID]) -> None:
        self._ids = iter(ids)

    def next_id(self) -> UUID:
        try:
            return next(self._ids)
        except StopIteration as exc:
            raise RuntimeError("No IDs remaining.") from exc
