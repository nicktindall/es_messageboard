from __future__ import annotations

from uuid import uuid4

import pytest

from messageboard.application import MessageBoards
from messageboard.domain import (
    MessageBoard,
    MessageNotFoundError,
    MissingFieldValueError,
    PermissionDeniedError,
)
from messageboard.test_util import assert_contains_event

ADMIN_ID = uuid4()
USER_ID = uuid4()


def test_create_message_board_fails_with_invalid_name() -> None:
    app = MessageBoards()
    with pytest.raises(MissingFieldValueError):
        app.create_message_board("", ADMIN_ID)


def test_post_message_fails_when_test_is_blank() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    with pytest.raises(MissingFieldValueError):
        app.post_message(board_id, "", None, USER_ID)


def test_post_message_fails_with_invalid_reply_to() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    with pytest.raises(MessageNotFoundError):
        app.post_message(board_id, "message text", 99, USER_ID)


def test_post_message_with_valid_reply_to() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    app.post_message(board_id, "message text", None, USER_ID)
    reply_id = app.post_message(board_id, "message text", 0, USER_ID)
    assert_contains_event(
        app.repository,
        board_id,
        MessageBoard.MessagePostedEvent,
        lambda e: e.message_id == reply_id and e.reply_to == 0,
    )


def test_post_message_with_non_moderated_user() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    message_id = app.post_message(board_id, "message text", None, USER_ID)
    assert_contains_event(
        app.repository,
        board_id,
        MessageBoard.MessagePostedEvent,
        lambda e: e.message_id == message_id and e.requires_moderation is False,
    )


def test_post_message_with_moderated_user() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    app.moderate_user(board_id, USER_ID, ADMIN_ID)
    message_id = app.post_message(board_id, "message text", None, USER_ID)
    assert_contains_event(
        app.repository,
        board_id,
        MessageBoard.MessagePostedEvent,
        lambda e: e.message_id == message_id and e.requires_moderation is True,
    )


def test_messages_return_incrementing_ids() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    assert app.post_message(board_id, "message text", None, USER_ID) == 0
    assert app.post_message(board_id, "message text", None, USER_ID) == 1
    assert app.post_message(board_id, "message text", None, USER_ID) == 2


def test_moderate_user_as_admin() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    app.moderate_user(board_id, USER_ID, ADMIN_ID)
    assert_contains_event(
        app.repository,
        board_id,
        MessageBoard.UserFlaggedForModerationEvent,
        lambda e: e.user_id == USER_ID,
    )


def test_moderate_user_as_non_admin() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    with pytest.raises(PermissionDeniedError):
        app.moderate_user(board_id, ADMIN_ID, USER_ID)


def test_approve_message_as_admin() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    app.moderate_user(board_id, USER_ID, ADMIN_ID)
    message_id = app.post_message(board_id, "message text", None, USER_ID)
    app.approve_message(board_id, message_id, ADMIN_ID)
    assert_contains_event(
        app.repository,
        board_id,
        MessageBoard.MessageApprovedEvent,
        lambda e: e.message_id == message_id,
    )


def test_approve_message_as_non_admin() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    app.moderate_user(board_id, USER_ID, ADMIN_ID)
    message_id = app.post_message(board_id, "message text", None, USER_ID)
    with pytest.raises(PermissionDeniedError):
        app.approve_message(board_id, message_id, USER_ID)


def test_approve_non_existent_message() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    app.moderate_user(board_id, USER_ID, ADMIN_ID)
    with pytest.raises(MessageNotFoundError):
        app.approve_message(board_id, 0, ADMIN_ID)


def test_reject_message_as_admin() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    app.moderate_user(board_id, USER_ID, ADMIN_ID)
    message_id = app.post_message(board_id, "message text", None, USER_ID)
    app.reject_message(board_id, message_id, ADMIN_ID)
    assert_contains_event(
        app.repository,
        board_id,
        MessageBoard.MessageRejectedEvent,
        lambda e: e.message_id == message_id,
    )


def test_reject_message_as_non_admin() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    app.moderate_user(board_id, USER_ID, ADMIN_ID)
    message_id = app.post_message(board_id, "message text", None, USER_ID)
    with pytest.raises(PermissionDeniedError):
        app.reject_message(board_id, message_id, USER_ID)


def test_reject_non_existent_message() -> None:
    app = MessageBoards()
    board_id = app.create_message_board("Test board", ADMIN_ID)
    with pytest.raises(MessageNotFoundError):
        app.reject_message(board_id, 0, ADMIN_ID)
