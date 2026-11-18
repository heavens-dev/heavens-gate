from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.watchdog.events import ConnectionEvents


@pytest.fixture
def connection_events(db, wg_hub, xray_worker):
    return ConnectionEvents(wg_hub, xray_worker)

@pytest.mark.asyncio
async def test_emit_connect(connection_events: ConnectionEvents):
    triggered_func = AsyncMock()

    client = Mock()
    client.userdata = Mock()

    peer = Mock()
    peer.peer_id = 1
    peer.status = PeerStatusChoices.STATUS_DISCONNECTED

    connection_events.connected.register(triggered_func)
    await connection_events.emit_connect(client, peer)

    triggered_func.assert_called_once_with(client, peer)
    client.set_peer_status.assert_called_once_with(peer.peer_id, PeerStatusChoices.STATUS_CONNECTED)
    client.set_status.assert_called_once_with(ClientStatusChoices.STATUS_CONNECTED)

    assert peer.status == PeerStatusChoices.STATUS_CONNECTED

@pytest.mark.asyncio
async def test_emit_disconnect(connection_events: ConnectionEvents):
    triggered_func = AsyncMock()

    client = Mock()
    client.get_connected_peers.return_value = []
    client.userdata = Mock()

    peer = Mock()
    peer.peer_id = 1
    peer.status = PeerStatusChoices.STATUS_CONNECTED

    connection_events.disconnected.register(triggered_func)
    await connection_events.emit_disconnect(client, peer)

    triggered_func.assert_called_once_with(client, peer)
    client.set_peer_status.assert_called_once_with(peer.peer_id, PeerStatusChoices.STATUS_DISCONNECTED)
    client.set_status.assert_called_once_with(ClientStatusChoices.STATUS_DISCONNECTED)

    assert peer.status == PeerStatusChoices.STATUS_DISCONNECTED

@pytest.mark.asyncio
async def test_emit_disconnect_with_connected_peers(connection_events: ConnectionEvents):
    triggered_func = AsyncMock()

    client = Mock()
    client.get_connected_peers.return_value = [Mock()]
    client.userdata = Mock()

    peer = Mock()
    peer.peer_id = 1
    peer.status = PeerStatusChoices.STATUS_CONNECTED

    connection_events.disconnected.register(triggered_func)
    await connection_events.emit_disconnect(client, peer)

    triggered_func.assert_called_once_with(client, peer)
    client.set_peer_status.assert_called_once_with(peer.peer_id, PeerStatusChoices.STATUS_DISCONNECTED)
    client.set_status.assert_not_called()

    assert peer.status == PeerStatusChoices.STATUS_DISCONNECTED

@pytest.mark.asyncio
async def test_emit_timeout(connection_events: ConnectionEvents):
    triggered_func = AsyncMock()

    client = Mock()
    client.userdata = Mock()
    client.get_connected_peers.return_value = []

    peer = Mock()
    peer.peer_id = 1
    peer.status = PeerStatusChoices.STATUS_CONNECTED

    connection_events.disconnected.register(triggered_func)
    with patch("core.wg.wg_work.WGHub.disable_peer"):
        await connection_events.emit_timeout_disconnect(client, peer)

    triggered_func.assert_called_once_with(client, peer)
    client.set_peer_status.assert_called_once_with(peer.peer_id, PeerStatusChoices.STATUS_TIME_EXPIRED)
    client.set_status.assert_called_once_with(ClientStatusChoices.STATUS_TIME_EXPIRED)

    assert peer.status == PeerStatusChoices.STATUS_TIME_EXPIRED


def test_update_client_peers_skips_untracked_client(connection_events: ConnectionEvents):
    connection_events.clients = []

    client = Mock()
    client.userdata = Mock()
    client.userdata.user_id = 123
    client.get_all_peers.return_value = []

    # Must not raise TypeError after the client was removed from the observer.
    connection_events.update_client_peers(client)

    assert connection_events.clients == []


def test_update_client_peers_updates_tracked_client(connection_events: ConnectionEvents):
    tracked_client = Mock()
    tracked_client.userdata = Mock()
    tracked_client.userdata.user_id = 123
    connection_events.clients = [(tracked_client, [])]

    updated_client = Mock()
    updated_client.userdata = Mock()
    updated_client.userdata.user_id = 123
    updated_client.get_all_peers.return_value = [Mock()]

    connection_events.update_client_peers(updated_client)

    assert connection_events.clients == [(updated_client, updated_client.get_all_peers.return_value)]


@pytest.mark.asyncio
async def test_remove_client_stops_tracking_client(connection_events: ConnectionEvents):
    first_client = Mock()
    first_client.userdata = Mock()
    first_client.userdata.user_id = 1
    second_client = Mock()
    second_client.userdata = Mock()
    second_client.userdata.user_id = 2
    connection_events.clients = [(first_client, []), (second_client, [])]

    await connection_events.remove_client(1)

    assert connection_events.clients == [(second_client, [])]


@pytest.mark.asyncio
async def test_update_client_peers_after_removal_does_not_raise(connection_events: ConnectionEvents):
    client = Mock()
    client.userdata = Mock()
    client.userdata.user_id = 1
    client.get_all_peers.return_value = []
    connection_events.clients = [(client, [])]

    await connection_events.remove_client(1)
    connection_events.update_client_peers(client)

    assert connection_events.clients == []
