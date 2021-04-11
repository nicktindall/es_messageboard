from typing import Optional
from uuid import UUID, uuid4

from eventsourcing.domain import Aggregate, AggregateCreated, AggregateEvent

FIRST_MESSAGE_ID = 0


class MessageBoard(Aggregate):
    """
    Message Board aggregate for event sourced example
    """

    def __init__(self, name: str, created_by: UUID):
        self.admin_user_ids: set[UUID] = set()
        self.moderated_users: set[UUID] = set()
        self.messages_awaiting_moderation: set[int] = set()
        self.rejected_messages: set[int] = set()
        self.next_message_id = FIRST_MESSAGE_ID

    @classmethod
    def create(cls, name: str, created_by: UUID) -> "MessageBoard":
        """
        Create a new message board
        """
        if not name:
            raise MissingFieldValueError("Name is required")
        board = cls._create(
            cls.MessageBoardCreatedEvent, id=uuid4(), name=name, created_by=created_by
        )
        board.trigger_event(cls.AdministratorAddedEvent, user_id=created_by)
        return board

    class MessageBoardCreatedEvent(AggregateCreated):
        name: str
        created_by: UUID

    class AdministratorAddedEvent(AggregateEvent):
        user_id: UUID

        def apply(self, aggregate: "MessageBoard") -> None:
            aggregate.admin_user_ids.add(self.user_id)

    def post_message(self, text: str, reply_to: Optional[int], author_id: UUID) -> int:
        """
        Post a new message to the message board
        """
        if not text:
            raise MissingFieldValueError("Message text must be non-blank")
        if reply_to is not None:
            self._assert_message_is_published(reply_to)
        message_id = self.next_message_id
        self.trigger_event(
            self.MessagePostedEvent,
            message_id=message_id,
            text=text,
            reply_to=reply_to,
            author_id=author_id,
            requires_moderation=self._user_is_moderated(author_id),
        )
        return message_id

    class MessagePostedEvent(AggregateEvent):
        message_id: int
        text: str
        reply_to: int
        author_id: UUID
        requires_moderation: bool

        def apply(self, aggregate: "MessageBoard") -> None:
            aggregate.next_message_id = aggregate.next_message_id + 1
            if self.requires_moderation:
                aggregate.messages_awaiting_moderation.add(self.message_id)

    def moderate_user(self, user_to_moderate: UUID, acting_user_id: UUID) -> None:
        """
        Flag that a users messages must be be approved before they are published

        :param user_to_moderate: The user to moderate
        :param acting_user_id: The user flagging the user for moderation
        """
        self._assert_user_is_admin(
            acting_user_id, "Only admins can flag users for moderation"
        )
        self.trigger_event(self.UserFlaggedForModerationEvent, user_id=user_to_moderate)

    class UserFlaggedForModerationEvent(AggregateEvent):
        user_id: UUID

        def apply(self, aggregate: "MessageBoard") -> None:
            aggregate.moderated_users.add(self.user_id)

    def approve_message(self, message_id: int, approver_id: UUID) -> None:
        """
        Approve a message awaiting moderation

        :param message_id: The message ID
        :param approver_id: The ID of the user approving
        :return:
        """
        self._assert_user_is_admin(approver_id, "Only admins can moderate messages")
        self._assert_message_is_awaiting_moderation(message_id)
        self.trigger_event(self.MessageApprovedEvent, message_id=message_id)

    class MessageApprovedEvent(AggregateEvent):
        message_id: int

        def apply(self, aggregate: "MessageBoard") -> None:
            aggregate.messages_awaiting_moderation.remove(self.message_id)

    def reject_message(self, message_id: int, rejecter_id: UUID) -> None:
        """
        Reject a message awaiting moderation

        :param message_id: The message ID
        :param rejecter_id: The ID of the user rejecting
        """
        self._assert_user_is_admin(rejecter_id, "Only admins can moderate messages")
        self._assert_message_is_awaiting_moderation(message_id)
        self.trigger_event(self.MessageRejectedEvent, message_id=message_id)

    class MessageRejectedEvent(AggregateEvent):
        message_id: int

        def apply(self, aggregate: "MessageBoard") -> None:
            aggregate.messages_awaiting_moderation.remove(self.message_id)
            aggregate.rejected_messages.add(self.message_id)

    def _user_is_moderated(self, user_id: UUID) -> bool:
        """
        Do messages from this user require moderation?

        :param user_id: The user ID
        :return: true if messages from that user require moderation, false otherwise
        """
        return user_id in self.moderated_users

    def _assert_message_is_published(self, message_id: int) -> None:
        if not (
            FIRST_MESSAGE_ID <= message_id < self.next_message_id
            and message_id not in self.messages_awaiting_moderation
            and message_id not in self.rejected_messages
        ):
            raise MessageNotFoundError(f"No published message with ID {message_id} ")

    def _assert_user_is_admin(self, user_id: UUID, message: str) -> None:
        if user_id not in self.admin_user_ids:
            raise PermissionDeniedError(message)

    def _assert_message_is_awaiting_moderation(self, message_id: int) -> None:
        if message_id not in self.messages_awaiting_moderation:
            raise MessageNotFoundError(
                f"Message {message_id} is not awaiting moderation"
            )


class MissingFieldValueError(Exception):
    pass


class MessageNotFoundError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass
