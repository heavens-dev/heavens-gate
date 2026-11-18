import datetime
from unittest.mock import Mock

from remnawave.exceptions import NotFoundError

from core.db.enums import ClientStatusChoices
from core.db.model_serializer import User
from core.utils.uuid_utils import generate_deterministic_uuid_string


def make_user(**kwargs) -> User:
    defaults = {
        "user_id": 100,
        "name": "test_user",
        "status": ClientStatusChoices.STATUS_CREATED,
        "registered_at": datetime.datetime.now(),
    }
    return User(**{**defaults, **kwargs})


def test_remnawave_delete_user_returns_true_on_success(xray_worker):
    user = make_user(user_id=100)
    xray_worker.remnawave = Mock()
    xray_worker._run_async = Mock()

    assert xray_worker.remnawave_delete_user(user) is True
    xray_worker.remnawave.users.delete_user.assert_called_once_with(
        uuid=generate_deterministic_uuid_string(str(user.user_id))
    )


def test_remnawave_delete_user_uses_stored_uuid(xray_worker):
    user = make_user(user_id=101, remnawave_user_uuid="stored-uuid")
    xray_worker.remnawave = Mock()
    xray_worker._run_async = Mock()

    assert xray_worker.remnawave_delete_user(user) is True
    xray_worker.remnawave.users.delete_user.assert_called_once_with(uuid="stored-uuid")


def test_remnawave_delete_user_treats_not_found_as_success(xray_worker):
    user = make_user(user_id=102)
    not_found = NotFoundError.__new__(NotFoundError)

    def raise_not_found(coro):
        raise not_found

    xray_worker.remnawave = Mock()
    xray_worker._run_async = raise_not_found

    assert xray_worker.remnawave_delete_user(user) is True


def test_remnawave_delete_user_returns_false_on_api_error(xray_worker):
    user = make_user(user_id=103)

    def raise_api_error(coro):
        raise RuntimeError("Remnawave is unavailable")

    xray_worker.remnawave = Mock()
    xray_worker._run_async = raise_api_error

    assert xray_worker.remnawave_delete_user(user) is False
