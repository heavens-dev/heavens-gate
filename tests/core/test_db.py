import pytest

from core.db.db_works import Client, ClientFactory


def test_create_client(db):
    ClientFactory(tg_id=123).get_or_create_client(name="iamuser", ip_address="127.0.0.1")

    client = ClientFactory(tg_id=123).get_client()

    assert isinstance(client, Client)
    assert client.userdata.name == "iamuser"
    assert client.userdata.telegram_id == 123
    assert client.userdata.ip_address == "127.0.0.1"

def test_add_peer(db, default_peers):
    client = ClientFactory(tg_id=123).get_or_create_client(name="iamuser")

    assert isinstance(client, Client)

    client.add_peer(**default_peers["iamuser_0"].model_dump(include={
        "shared_ips", "public_key", "private_key", "preshared_key", "peer_name"
    }))
    client.add_peer(**default_peers["iamuser_1"].model_dump(include={
        "shared_ips", "public_key", "private_key", "preshared_key", "peer_name"
    }))

    peers = client.get_peers()

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
