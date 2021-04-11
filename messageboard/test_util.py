from typing import Callable, Type, TypeVar
from uuid import UUID

from eventsourcing.application import Repository
from eventsourcing.domain import AggregateEvent

E = TypeVar("E", bound=AggregateEvent)


def assert_contains_event(
    repository: Repository,
    board_id: UUID,
    type_: Type[E],
    assertions: Callable[[E], bool],
) -> None:
    for e in repository.event_store.get(board_id):
        print(e)
        if isinstance(e, type_) and assertions(e):
            return
    raise AssertionError("Event not found")
