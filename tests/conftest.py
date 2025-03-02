import pytest

from core.db.enums import PeerStatusChoices
from core.db.model_serializer import ConnectionPeer
from core.db.models import init_db
from core.wg.wg_work import WGHub

DEFAULT_PEERS = {
    "iamuser_0": ConnectionPeer(
        id=0,
        user_id=1,
        peer_name="iamuser_0",
        public_key="fDW0TEh64L1qlcuNF5dSSRIhxImrCBECje2r2vXBcXI=",
        preshared_key="OGsOqOc7uoHW2DkXoZzwVxpwaSTNxQeyXZ9ukc58rgE=",
        private_key="+HBpjH+3M0/CFRGjoi5uKy6okJRzHo87X0XP+37hUFw=",
        peer_status=PeerStatusChoices.STATUS_DISCONNECTED,
        shared_ips="10.0.0.2/32",
        is_amnezia=False,
    ),
    "iamuser_1": ConnectionPeer(
        id=1,
        user_id=1,
        peer_name="iamuser_1",
        public_key="Nts96aOJMVfQEZXt54q3MF1S7WVAGC/SDvpzN/mFXhw=",
        preshared_key="n3Fx4vZBLA6ps/Tw/s1GrVgM4oKKto4TU1ZuJBg1vao=",
        private_key="+HBpjH+3M0/CFRGjoi5uKy6okJRzHo87X0XP+37hUFw=",
        peer_status=PeerStatusChoices.STATUS_DISCONNECTED,
        shared_ips="10.0.0.3/32",
        is_amnezia=False
    ),
    "otheruser_2": ConnectionPeer(
        id=2,
        user_id=2,
        peer_name="otheruser_2",
        public_key="0uJLDEnjhokgSt6GAl5VErvqsVBJAS37k85cSKLPNiI=",
        preshared_key="WdOuOBVtO0Th5ZPtWFcMrpJ8PVaB8KfIQfprFVuJADc=",
        private_key="+HBpjH+3M0/CFRGjoi5uKy6okJRzHo87X0XP+37hUFw=",
        peer_status=PeerStatusChoices.STATUS_DISCONNECTED,
        shared_ips="10.0.0.4/32",
        is_amnezia=False
    ),
}

@pytest.fixture(scope="function")
def default_peers() -> dict[str, ConnectionPeer]:
    return DEFAULT_PEERS

@pytest.fixture(scope="function")
def wg_hub(tmp_path):
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
