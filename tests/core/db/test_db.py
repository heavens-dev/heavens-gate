import pytest

from core.db.db_works import Client, ClientFactory
from core.db.models import PeerModel
from core.db.serializer_extensions import SerializerExtensions


def test_create_client(db):
    ClientFactory(user_id=123).get_or_create_client(name="iamuser")

    client = ClientFactory(user_id=123).get_client()

    assert isinstance(client, Client)
    assert client.userdata.name == "iamuser"
    assert client.userdata.user_id == "123"

def test_add_and_get_wireguard_peers(db, default_peers):
    client, is_created = ClientFactory(user_id=123).get_or_create_client(name="iamuser")

    assert is_created is True
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
    assert peers[0].name == default_peers["iamuser_0"].name
    assert peers[0].shared_ips == default_peers["iamuser_0"].shared_ips
    assert peers[0].public_key == default_peers["iamuser_0"].public_key
    assert peers[0].private_key == default_peers["iamuser_0"].private_key
    assert peers[0].preshared_key == default_peers["iamuser_0"].preshared_key

    assert peers[1].name == default_peers["iamuser_1"].name
    assert peers[1].shared_ips == default_peers["iamuser_1"].shared_ips
    assert peers[1].public_key == default_peers["iamuser_1"].public_key
    assert peers[1].private_key == default_peers["iamuser_1"].private_key
    assert peers[1].preshared_key == default_peers["iamuser_1"].preshared_key

def test_delete_wireguard_peer(db, default_peers):
    client, is_created = ClientFactory(user_id=123).get_or_create_client(name="iamuser")

    assert is_created is True
    assert isinstance(client, Client)

    peer = client.add_wireguard_peer(**default_peers["iamuser_0"].model_dump(include={
        "shared_ips", "public_key", "private_key", "preshared_key"
    }))

    assert peer is not None

    ClientFactory.delete_peer(peer=peer)

    peers = client.get_wireguard_peers(is_amnezia=False)

    assert len(peers) == 0

def test_add_xray_peer(db):
    client, is_created = ClientFactory(user_id=1234).get_or_create_client(name="xrayuser")

    assert is_created is True
    assert isinstance(client, Client)

    peer = client.add_xray_peer(inbound_id=123, flow="flow")

    assert peer is not None

    assert peer.flow == "flow"
    assert peer.inbound_id == 123
    assert peer.hash_id is not None


def test_serializer_extensions_get_user_from_peer_model(db):
    client, _ = ClientFactory(user_id=777).get_or_create_client(name="serializer_user")
    peer = client.add_wireguard_peer(shared_ips="10.0.0.7/32")

    assert peer is not None

    peer_model = PeerModel.get_by_id(peer.peer_id)
    user = SerializerExtensions.get_user_from_peer_model(peer_model)

    assert user is not None
    assert user.user_id == "777"
    assert user.name == "serializer_user"


def test_serializer_extensions_get_user_from_serialized_peer(db):
    client, _ = ClientFactory(user_id=778).get_or_create_client(name="serialized_peer_user")
    peer = client.add_wireguard_peer(shared_ips="10.0.0.8/32")

    assert peer is not None

    user = SerializerExtensions.get_user_from_peer(peer)

    assert user is not None
    assert user.user_id == "778"
    assert user.name == "serialized_peer_user"
