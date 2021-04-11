from uuid import uuid4

from eventsourcing.system import SingleThreadedRunner, System

from messageboard.application import MessageBoards
from messageboard.projections.posts_repo import PostRepository

ADMIN_ID = uuid4()
USER_ID = uuid4()


def test_posts_are_included() -> None:
    system = System(pipes=[[MessageBoards, PostRepository]])
    runner = SingleThreadedRunner(system)
    runner.start()

    message_boards = runner.get(MessageBoards)
    posts_repo = runner.get(PostRepository)

    board_id = message_boards.create_message_board("Foobar board", ADMIN_ID)
    post_id = message_boards.post_message(board_id, "the message", None, USER_ID)

    # Test posts repo
    assert posts_repo.get_post(board_id, post_id) is not None


def test_replies_are_linked_up() -> None:
    system = System(pipes=[[MessageBoards, PostRepository]])
    runner = SingleThreadedRunner(system)
    runner.start()

    message_boards = runner.get(MessageBoards)
    posts_repo = runner.get(PostRepository)

    board_id = message_boards.create_message_board("Foobar board", ADMIN_ID)
    original_message_id = message_boards.post_message(
        board_id, "Original", None, USER_ID
    )
    reply_message_id = message_boards.post_message(
        board_id, "Reply", original_message_id, USER_ID
    )

    assert posts_repo.get_post(board_id, original_message_id).replies[
        0
    ] == posts_repo.get_post(board_id, reply_message_id)


def test_published_field_is_set_when_moderated_post_is_approved() -> None:
    system = System(pipes=[[MessageBoards, PostRepository]])
    runner = SingleThreadedRunner(system)
    runner.start()

    message_boards = runner.get(MessageBoards)
    posts_repo = runner.get(PostRepository)

    board_id = message_boards.create_message_board("Foobar board", ADMIN_ID)
    message_boards.moderate_user(board_id, USER_ID, ADMIN_ID)
    message_id = message_boards.post_message(board_id, "Original", None, USER_ID)
    assert not posts_repo.get_post(board_id, message_id).published

    message_boards.approve_message(board_id, message_id, ADMIN_ID)
    assert posts_repo.get_post(board_id, message_id).published
