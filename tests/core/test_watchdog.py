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
    peer.peer_status = PeerStatusChoices.STATUS_DISCONNECTED

    connection_events.connected.register(triggered_func)
    await connection_events.emit_connect(client, peer)

    triggered_func.assert_called_once_with(client, peer)
    client.set_peer_status.assert_called_once_with(peer.peer_id, PeerStatusChoices.STATUS_CONNECTED)
    client.set_status.assert_called_once_with(ClientStatusChoices.STATUS_CONNECTED)

    assert peer.peer_status == PeerStatusChoices.STATUS_CONNECTED

@pytest.mark.asyncio
async def test_emit_disconnect(connection_events: ConnectionEvents):
    triggered_func = AsyncMock()

    client = Mock()
    client.get_connected_peers.return_value = []
    client.userdata = Mock()

    peer = Mock()
    peer.peer_id = 1
    peer.peer_status = PeerStatusChoices.STATUS_CONNECTED

    connection_events.disconnected.register(triggered_func)
    await connection_events.emit_disconnect(client, peer)

    triggered_func.assert_called_once_with(client, peer)
    client.set_peer_status.assert_called_once_with(peer.peer_id, PeerStatusChoices.STATUS_DISCONNECTED)
    client.set_status.assert_called_once_with(ClientStatusChoices.STATUS_DISCONNECTED)

    assert peer.peer_status == PeerStatusChoices.STATUS_DISCONNECTED

@pytest.mark.asyncio
async def test_emit_disconnect_with_connected_peers(connection_events: ConnectionEvents):
    triggered_func = AsyncMock()

    client = Mock()
    client.get_connected_peers.return_value = [Mock()]
    client.userdata = Mock()

    peer = Mock()
    peer.peer_id = 1
    peer.peer_status = PeerStatusChoices.STATUS_CONNECTED

    connection_events.disconnected.register(triggered_func)
    await connection_events.emit_disconnect(client, peer)

    triggered_func.assert_called_once_with(client, peer)
    client.set_peer_status.assert_called_once_with(peer.peer_id, PeerStatusChoices.STATUS_DISCONNECTED)
    client.set_status.assert_not_called()

    assert peer.peer_status == PeerStatusChoices.STATUS_DISCONNECTED

@pytest.mark.asyncio
async def test_emit_timeout(connection_events: ConnectionEvents):
    triggered_func = AsyncMock()

    client = Mock()
    client.userdata = Mock()
    client.get_connected_peers.return_value = []

    peer = Mock()
    peer.peer_id = 1
    peer.peer_status = PeerStatusChoices.STATUS_CONNECTED

    connection_events.disconnected.register(triggered_func)
    with patch("core.wg.wg_work.WGHub.disable_peer"):
        await connection_events.emit_timeout_disconnect(client, peer)

    triggered_func.assert_called_once_with(client, peer)
    client.set_peer_status.assert_called_once_with(peer.peer_id, PeerStatusChoices.STATUS_TIME_EXPIRED)
    client.set_status.assert_called_once_with(ClientStatusChoices.STATUS_TIME_EXPIRED)

    assert peer.peer_status == PeerStatusChoices.STATUS_TIME_EXPIRED
