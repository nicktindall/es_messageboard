from uuid import uuid4

from eventsourcing.system import SingleThreadedRunner, System

from messageboard.application import MessageBoards
from messageboard.projections.posts_by_user_index import PostsByUserIndex

ADMIN_ID = uuid4()
USER_ID = uuid4()


def test_posts_are_indexed() -> None:
    system = System(pipes=[[MessageBoards, PostsByUserIndex]])
    runner = SingleThreadedRunner(system)
    runner.start()

    message_boards = runner.get(MessageBoards)
    posts_by_user_index = runner.get(PostsByUserIndex)

    board_id = message_boards.create_message_board("Foobar board", ADMIN_ID)
    post_id = message_boards.post_message(board_id, "the message", None, USER_ID)

    assert posts_by_user_index.get_posts_for_user(USER_ID) == {(board_id, post_id)}


def test_moderated_posts_are_not_indexed_until_approved() -> None:
    system = System(pipes=[[MessageBoards, PostsByUserIndex]])
    runner = SingleThreadedRunner(system)
    runner.start()

    message_boards = runner.get(MessageBoards)
    posts_by_user_index = runner.get(PostsByUserIndex)

    board_id = message_boards.create_message_board("Foobar board", ADMIN_ID)
    other_board_id = message_boards.create_message_board("Other board", ADMIN_ID)
    message_boards.moderate_user(other_board_id, USER_ID, ADMIN_ID)

    message_boards.post_message(board_id, "whooo", None, USER_ID)
    message_boards.post_message(board_id, "whooo", None, USER_ID)
    moderated_message = message_boards.post_message(
        other_board_id, "whooo", None, USER_ID
    )

    assert len(posts_by_user_index.get_posts_for_user(USER_ID)) == 2
    message_boards.approve_message(other_board_id, moderated_message, ADMIN_ID)
    assert len(posts_by_user_index.get_posts_for_user(USER_ID)) == 3
