import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from bot.utils.delete_user import (delete_preview_text, is_bot_admin,
                                   purge_client)
from core.db.db_works import ClientFactory
from core.db.enums import ProtocolType, SubscriptionType


@pytest.fixture
def cleanup_calls():
    return []


@pytest.fixture
def client():
    wg_peer = SimpleNamespace(type=ProtocolType.WIREGUARD, shared_ips="10.0.0.2/32")
    amnezia_peer = SimpleNamespace(type=ProtocolType.AMNEZIA_WIREGUARD, shared_ips="10.0.0.3/32")
    xray_peer = SimpleNamespace(type=ProtocolType.XRAY)

    client = Mock()
    client.userdata = SimpleNamespace(user_id=42, name="test_user")
    client.get_all_peers.return_value = [wg_peer, amnezia_peer]
    client.get_xray_peers.return_value = [xray_peer]
    return client


@pytest.mark.asyncio
async def test_purge_client_cleans_up_external_systems_before_database(client, cleanup_calls):
    def record(label, result=True):
        def _side_effect(*args, **kwargs):
            cleanup_calls.append(label)
            return result
        return _side_effect

    async def record_remove(user_id):
        cleanup_calls.append("remove_client")

    wghub = Mock()
    wghub.delete_peer.side_effect = record("wg_delete_peer")
    ip_queue = Mock()
    ip_queue.release_ip.side_effect = record("release_ip")
    xray_worker = Mock()
    xray_worker.remnawave = Mock()
    xray_worker.remnawave_delete_user.side_effect = record("remnawave_delete_user")
    xray_worker.delete_peer.side_effect = record("xray_delete_peer")
    connections_observer = Mock()
    connections_observer.remove_client = AsyncMock(side_effect=record_remove)

    with patch(
        "bot.utils.delete_user.ClientFactory.delete_client_by_id",
        side_effect=record("db_delete_client")
    ):
        assert await purge_client(
            client,
            wghub=wghub,
            xray_worker=xray_worker,
            ip_queue=ip_queue,
            connections_observer=connections_observer
        ) is True

    assert cleanup_calls == [
        "remnawave_delete_user",
        "wg_delete_peer",
        "release_ip",
        "wg_delete_peer",
        "release_ip",
        "xray_delete_peer",
        "remove_client",
        "db_delete_client",
    ]
    wghub.delete_peer.assert_any_call(client.get_all_peers.return_value[0])
    wghub.delete_peer.assert_any_call(client.get_all_peers.return_value[1])
    ip_queue.release_ip.assert_any_call("10.0.0.2/32")
    ip_queue.release_ip.assert_any_call("10.0.0.3/32")
    xray_worker.delete_peer.assert_called_once_with(client.get_xray_peers.return_value[0])
    connections_observer.remove_client.assert_awaited_once_with(client.userdata.user_id)


@pytest.mark.asyncio
async def test_purge_client_keeps_database_record_when_remnawave_fails(client):
    wghub = Mock()
    ip_queue = Mock()
    xray_worker = Mock()
    xray_worker.remnawave = Mock()
    xray_worker.remnawave_delete_user.return_value = False
    connections_observer = Mock()
    connections_observer.remove_client = AsyncMock()

    with patch("bot.utils.delete_user.ClientFactory.delete_client_by_id") as db_delete:
        assert await purge_client(
            client,
            wghub=wghub,
            xray_worker=xray_worker,
            ip_queue=ip_queue,
            connections_observer=connections_observer
        ) is False

    wghub.delete_peer.assert_not_called()
    ip_queue.release_ip.assert_not_called()
    xray_worker.delete_peer.assert_not_called()
    connections_observer.remove_client.assert_not_awaited()
    db_delete.assert_not_called()


def test_delete_preview_text_shows_only_identification_data():
    client = Mock()
    client.userdata = SimpleNamespace(
        name="Vasya",
        user_id=42,
        subscription_type=SubscriptionType.DEFAULT,
        subscription_expiry=datetime.datetime(2026, 12, 1),
    )
    client.is_org_member.return_value = SimpleNamespace(name="Acme", org_id=7)
    client.get_owned_org.return_value = None

    text = delete_preview_text(client)

    assert "Vasya" in text
    assert "<code>42</code>" in text
    assert "01.12.2026" in text
    assert "Classic" in text
    assert "Acme" in text
    assert "пир" not in text.lower()
    assert "ссылк" not in text.lower()
    assert "статус" not in text.lower()
    assert "АБСОЛЮТНО ТОЧНО" not in text


def test_delete_preview_text_handles_missing_subscription_and_ownership_warning():
    client = Mock()
    client.userdata = SimpleNamespace(
        name="Vasya",
        user_id=42,
        subscription_type=None,
        subscription_expiry=None,
    )
    client.is_org_member.return_value = False
    client.get_owned_org.return_value = SimpleNamespace(
        orgdata=SimpleNamespace(name="Acme", org_id=7)
    )

    text = delete_preview_text(client, warning=True)

    assert "Подписка: нет, до нет" in text
    assert "владелец организации" in text
    assert "без владельца" in text
    assert "АБСОЛЮТНО ТОЧНО" in text


def test_is_bot_admin_matches_stored_string_id():
    assert is_bot_admin("272727", [272727, 282828]) is True
    assert is_bot_admin(272727, [272727, 282828]) is True
    assert is_bot_admin("12345", [272727, 282828]) is False


@pytest.mark.asyncio
async def test_purge_client_deletes_user_and_peers_from_database(db):
    client, _ = ClientFactory(user_id=555).get_or_create_client(name="db_user")
    peer = client.add_wireguard_peer("10.0.0.55/32")
    assert peer is not None

    wghub = Mock()
    ip_queue = Mock()
    xray_worker = Mock()
    xray_worker.remnawave = None
    connections_observer = Mock()
    connections_observer.remove_client = AsyncMock()

    assert await purge_client(
        client,
        wghub=wghub,
        xray_worker=xray_worker,
        ip_queue=ip_queue,
        connections_observer=connections_observer
    ) is True

    assert ClientFactory.get_client_by_id(555) is None
    assert ClientFactory.get_peer_by_id(peer.peer_id) is None
