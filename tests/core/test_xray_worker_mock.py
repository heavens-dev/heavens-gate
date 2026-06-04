from unittest.mock import Mock

import pytest

from core.xray.xray_worker import XrayWorker


def test_ignore_xui_api_does_not_construct_real_api(monkeypatch):
    real_api = Mock(side_effect=AssertionError("real 3x-ui Api should not be constructed"))
    monkeypatch.setattr("core.xray.xray_worker.Api", real_api)

    worker = XrayWorker(
        host="http://relay.heavensgate.ru",
        port="25565",
        web_path="",
        username="admin",
        password="password",
        ignore_xui_api=True,
    )

    real_api.assert_not_called()
    assert worker.api.login() is True
    assert worker.api.client.online() == []


def test_ignore_xui_api_mocks_private_login(monkeypatch):
    monkeypatch.setattr("core.xray.xray_worker.Api", Mock())

    worker = XrayWorker(
        host="http://relay.heavensgate.ru",
        port="25565",
        web_path="",
        username="admin",
        password="password",
        ignore_xui_api=True,
    )
    worker.api.login = Mock(side_effect=pytest.fail)

    assert worker._XrayWorker__login() is True
    worker.api.login.assert_not_called()
