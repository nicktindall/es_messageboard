from typing import Optional
from uuid import UUID

from eventsourcing.application import Application

from messageboard.domain import MessageBoard


class MessageBoards(Application):
    def create_message_board(self, name: str, created_by: UUID) -> UUID:
        board = MessageBoard.create(name, created_by)
        self.save(board)
        return board.id

    def post_message(
        self, board_id: UUID, text: str, reply_to: Optional[int], author_id: UUID
    ) -> int:
        board = self.repository.get(board_id)
        message_id = board.post_message(text, reply_to, author_id)
        self.save(board)
        return message_id

    def moderate_user(
        self, board_id: UUID, user_id: UUID, acting_user_id: UUID
    ) -> None:
        board = self.repository.get(board_id)
        board.moderate_user(user_id, acting_user_id)
        self.save(board)

    def approve_message(
        self, board_id: UUID, message_id: int, approver_id: UUID
    ) -> None:
        board = self.repository.get(board_id)
        board.approve_message(message_id, approver_id)
        self.save(board)

    def reject_message(
        self, board_id: UUID, message_id: int, rejecter_id: UUID
    ) -> None:
        board = self.repository.get(board_id)
        board.reject_message(message_id, rejecter_id)
        self.save(board)
