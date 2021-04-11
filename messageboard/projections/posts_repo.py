from dataclasses import dataclass, field
from functools import singledispatchmethod
from typing import Any, Dict, Optional
from uuid import UUID

from eventsourcing.domain import AggregateEvent
from eventsourcing.system import ProcessApplication, ProcessEvent

from messageboard.domain import MessageBoard


@dataclass
class Post:
    test: str
    author: UUID
    published: bool
    replies: list["Post"] = field(default_factory=list)


class PostRepository(ProcessApplication):
    """
    Keeps a repository of all posts indexed by board, message ID
    """

    def __init__(self):
        super().__init__()
        self._posts_by_board: dict[UUID, dict[int, Post]] = dict()

    @singledispatchmethod
    def policy(self, domain_event: AggregateEvent, process_event: ProcessEvent) -> None:
        pass

    @policy.register(MessageBoard.MessagePostedEvent)
    def _handle_post_created(
        self, domain_event: MessageBoard.MessagePostedEvent, process_event: Any
    ) -> None:
        post = Post(
            domain_event.text,
            domain_event.author_id,
            not domain_event.requires_moderation,
        )
        self._posts_by_board.setdefault(domain_event.originator_id, {})[
            domain_event.message_id
        ] = post
        if domain_event.reply_to is not None:
            self._posts_by_board[domain_event.originator_id][
                domain_event.reply_to
            ].replies.append(post)

    @policy.register(MessageBoard.MessageApprovedEvent)
    def _handle_post_approved(
        self, domain_event: MessageBoard.MessagePostedEvent, process_event: Any
    ) -> None:
        self._posts_by_board.setdefault(domain_event.originator_id, {})[
            domain_event.message_id
        ].published = True

    def get_post(self, board_id: UUID, post_id: int) -> Optional[Post]:
        if (
            board_id in self._posts_by_board
            and post_id in self._posts_by_board[board_id]
        ):
            return self._posts_by_board[board_id][post_id]
        return None
