import pytest

from core.db.db_works import Client, ClientFactory


def test_create_client(db):
    ClientFactory(user_id=123).get_or_create_client(name="iamuser")

    client = ClientFactory(user_id=123).get_client()

    assert isinstance(client, Client)
    assert client.userdata.name == "iamuser"
    assert client.userdata.user_id == "123"

def test_add_and_get_wireguard_peers(db, default_peers):
    client = ClientFactory(user_id=123).get_or_create_client(name="iamuser")

    assert isinstance(client, Client)

    peer1 = client.add_wireguard_peer(**default_peers["iamuser_0"].model_dump(include={
        "shared_ips", "public_key", "private_key", "preshared_key"
    }))
    peer2 = client.add_wireguard_peer(**default_peers["iamuser_1"].model_dump(include={
        "shared_ips", "public_key", "private_key", "preshared_key"
    }))

    assert peer1 is not None
    assert peer2 is not None

    peers = client.get_wireguard_peers(is_amnezia=False)

    assert len(peers) == 2
    assert peers[0].peer_name == default_peers["iamuser_0"].peer_name
    assert peers[0].shared_ips == default_peers["iamuser_0"].shared_ips
    assert peers[0].public_key == default_peers["iamuser_0"].public_key
    assert peers[0].private_key == default_peers["iamuser_0"].private_key
    assert peers[0].preshared_key == default_peers["iamuser_0"].preshared_key

    assert peers[1].peer_name == default_peers["iamuser_1"].peer_name
    assert peers[1].shared_ips == default_peers["iamuser_1"].shared_ips
    assert peers[1].public_key == default_peers["iamuser_1"].public_key
    assert peers[1].private_key == default_peers["iamuser_1"].private_key
    assert peers[1].preshared_key == default_peers["iamuser_1"].preshared_key

def test_delete_wireguard_peer(db, default_peers):
    client = ClientFactory(user_id=123).get_or_create_client(name="iamuser")

    assert isinstance(client, Client)

    peer = client.add_wireguard_peer(**default_peers["iamuser_0"].model_dump(include={
        "shared_ips", "public_key", "private_key", "preshared_key"
    }))

    assert peer is not None

    ClientFactory.delete_peer(peer=peer)

    peers = client.get_wireguard_peers(is_amnezia=False)

    assert len(peers) == 0

def test_add_xray_peer(db):
    client = ClientFactory(user_id=1234).get_or_create_client(name="xrayuser")

    assert isinstance(client, Client)

    peer = client.add_xray_peer(inbound_id=123, flow="flow")

    assert peer is not None

    assert peer.flow == "flow"
    assert peer.inbound_id == 123
