import pytest

from core.db.model_serializer import WireguardPeer
from core.wg.wg_work import WGHub


def test_disable_peer(wg_hub: WGHub, default_peers: dict[str, WireguardPeer]):
    wg_hub.disable_peer(default_peers["iamuser_0"])
    assert wg_hub.wgconfig.get_peer_enabled(default_peers["iamuser_0"].public_key) is False

def test_enable_peer(wg_hub: WGHub, default_peers: dict[str, WireguardPeer]):
    wg_hub.enable_peer(default_peers["iamuser_0"])
    assert wg_hub.wgconfig.get_peer_enabled(default_peers["iamuser_0"].public_key) is True

def test_add_peer(wg_hub: WGHub, default_peers: dict[str, WireguardPeer]):
    wg_hub.add_peer(default_peers["otheruser_2"])
    assert isinstance(wg_hub.wgconfig.get_peer(default_peers["otheruser_2"].public_key), dict)

    with pytest.raises(KeyError) as excinfo:
        wg_hub.add_peer(default_peers["otheruser_2"])

def test_delete_peer(wg_hub: WGHub, default_peers: dict[str, WireguardPeer]):
    wg_hub.delete_peer(default_peers["iamuser_0"])
    with pytest.raises(KeyError) as excinfo:
        wg_hub.wgconfig.get_peer(default_peers["otheruser_2"].public_key)

    with pytest.raises(KeyError) as excinfo:
        wg_hub.delete_peer(default_peers["otheruser_2"])
