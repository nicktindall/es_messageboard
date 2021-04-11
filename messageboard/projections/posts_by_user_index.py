from functools import singledispatchmethod
from typing import Any, Dict, Set, Tuple
from uuid import UUID

from eventsourcing.domain import AggregateEvent
from eventsourcing.system import ProcessApplication, ProcessEvent

from messageboard.domain import MessageBoard


class PostsByUserIndex(ProcessApplication):
    """
    Keeps an index of (board_id, message_id) tuples for each user_id.
    Only approved posts are included for moderated users.
    """

    def __init__(self):
        super().__init__()
        self._posts_awaiting_moderation: Dict[Tuple[UUID, int], UUID] = {}
        self._posts_by_user: Dict[UUID, Set[Tuple[UUID, int]]] = {}

    @singledispatchmethod
    def policy(self, domain_event: AggregateEvent, process_event: ProcessEvent) -> None:
        pass

    @policy.register(MessageBoard.MessagePostedEvent)
    def _handle_post_created(
        self, domain_event: MessageBoard.MessagePostedEvent, process_event: Any
    ) -> None:
        if domain_event.requires_moderation:
            self._posts_awaiting_moderation[
                (domain_event.originator_id, domain_event.message_id)
            ] = domain_event.author_id
        else:
            self._posts_by_user.setdefault(domain_event.author_id, set()).add(
                (domain_event.originator_id, domain_event.message_id)
            )

    @policy.register(MessageBoard.MessageApprovedEvent)
    def _handle_post_approved(
        self, domain_event: MessageBoard.MessagePostedEvent, process_event: Any
    ) -> None:
        message_tuple = (domain_event.originator_id, domain_event.message_id)
        author = self._posts_awaiting_moderation.pop(message_tuple)
        self._posts_by_user.setdefault(author, set()).add(message_tuple)

    @policy.register(MessageBoard.MessageRejectedEvent)
    def _handle_post_rejected(
        self, domain_event: MessageBoard.MessagePostedEvent, process_event: Any
    ) -> None:
        message_tuple = (domain_event.originator_id, domain_event.message_id)
        del self._posts_awaiting_moderation[message_tuple]

    def get_posts_for_user(self, user_id: UUID) -> Set[Tuple[UUID, int]]:
        return self._posts_by_user.get(user_id, set())
