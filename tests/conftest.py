import pytest

from config.settings import Config
from core.db.enums import PeerStatusChoices, ProtocolType
from core.db.model_serializer import WireguardPeer
from core.db.models import init_db
from core.wg.wg_work import WGHub

PRIVATE_KEY = "AMHCM2a1apUYPMnrpobc6Erjaz6r7z9rN9ieonhJK3U="

DEFAULT_PEERS = {
    "iamuser_0": WireguardPeer(
        id=0,
        user_id=1,
        peer_name="iamuser_0",
        public_key="fDW0TEh64L1qlcuNF5dSSRIhxImrCBECje2r2vXBcXI=",
        preshared_key="OGsOqOc7uoHW2DkXoZzwVxpwaSTNxQeyXZ9ukc58rgE=",
        private_key=PRIVATE_KEY,
        peer_status=PeerStatusChoices.STATUS_DISCONNECTED,
        shared_ips="10.0.0.2/32",
        is_amnezia=False,
        peer_type=ProtocolType.WIREGUARD
    ),
    "iamuser_1": WireguardPeer(
        id=1,
        user_id=1,
        peer_name="iamuser_1",
        public_key="Nts96aOJMVfQEZXt54q3MF1S7WVAGC/SDvpzN/mFXhw=",
        preshared_key="n3Fx4vZBLA6ps/Tw/s1GrVgM4oKKto4TU1ZuJBg1vao=",
        private_key=PRIVATE_KEY,
        peer_status=PeerStatusChoices.STATUS_DISCONNECTED,
        shared_ips="10.0.0.3/32",
        is_amnezia=False,
        peer_type=ProtocolType.WIREGUARD
    ),
    "otheruser_2": WireguardPeer(
        id=2,
        user_id=2,
        peer_name="otheruser_2",
        public_key="0uJLDEnjhokgSt6GAl5VErvqsVBJAS37k85cSKLPNiI=",
        preshared_key="WdOuOBVtO0Th5ZPtWFcMrpJ8PVaB8KfIQfprFVuJADc=",
        private_key=PRIVATE_KEY,
        peer_status=PeerStatusChoices.STATUS_DISCONNECTED,
        shared_ips="10.0.0.4/32",
        is_amnezia=False,
        peer_type=ProtocolType.WIREGUARD
    ),
}

@pytest.fixture(scope="function")
def default_peers() -> dict[str, WireguardPeer]:
    return DEFAULT_PEERS

@pytest.fixture(scope="function")
def wg_hub(tmp_path) -> WGHub:
    with open(tmp_path / "wg0.conf", "w+b") as wg_file:
        wg_file.write(b"""[Interface]
Address = 10.0.0.1/24, ffff:ffff:ffff:ffff::1/64
ListenPort = 12345
PrivateKey = +HBpjH+3M0/CFRGjoi5uKy6okJRzHo87X0XP+37hUFw=
MTU=1500

# iamuser_0
[Peer]
PublicKey = fDW0TEh64L1qlcuNF5dSSRIhxImrCBECje2r2vXBcXI=
PresharedKey = OGsOqOc7uoHW2DkXoZzwVxpwaSTNxQeyXZ9ukc58rgE=
AllowedIPs = 10.0.0.2/32

# iamuser_1
[Peer]
PublicKey = Nts96aOJMVfQEZXt54q3MF1S7WVAGC/SDvpzN/mFXhw=
PresharedKey = n3Fx4vZBLA6ps/Tw/s1GrVgM4oKKto4TU1ZuJBg1vao=
AllowedIPs = 10.0.0.3/32
""")
        wg_file.flush()
        return WGHub(wg_file.name, auto_sync=False)

@pytest.fixture(scope="module")
def db():

    db_instance = init_db(":memory:")

    yield

    db_instance.close()

@pytest.fixture(scope="function")
def wireguard_server_config():
    return Config.WireguardServer(
        path="wg0.conf",
        user_ip="10.0.0",
        user_ip_mask="24",
        public_key="qrpLJiZHfl+zKJrO4Uim7Xq1WaYpK1vDbG2WlMf4f3c=",
        private_key=PRIVATE_KEY,
        endpoint_ip="127.0.0.1",
        endpoint_port="12345",
        dns_server="8.8.8.8",
        junk=""
    )

@pytest.fixture(scope="function")
def config_path(tmp_path):
    path = tmp_path / "config.conf"
    with open(path, "w") as f:
        f.write("""
[TelegramBot]
token=1234567890:ABCDEF
admins=272727, 282828
faq_url=https://example.com/faq

[db]
path=db.sqlite

[core]
peer_active_time=12 # in hours
connection_listen_timer=2 # in seconds
connection_update_timer=5 # in seconds
connection_connected_only_listen_timer=1 # in seconds
logs_path=./logs

[Server]
Path=/etc/wireguard/wg0.conf
IP=10.0.0
IPMask=32
PrivateKey=+HBpjH+3M0/CFRGjoi5uKy6okJRzHo87X0XP+37hUFw=
EndpointIP=1.1.1.1
EndpointPort=8888
# Junk values that are only used in Amnezia WG. You should not enter them manually!
# setup.py will do all the dirty work for you
Junk=1,2,3,4,5""")

    return path
