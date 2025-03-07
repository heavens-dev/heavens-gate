from config.settings import Config
from core.wg.wgconfig_helper import get_peer_config_str


def test_get_peer_config_str(default_peers, server_config: Config.Server):
    peer = default_peers["iamuser_0"]
    assert get_peer_config_str(server_config, peer) == f"""[Interface]
Address = {peer.shared_ips}/{server_config.user_ip_mask}
DNS = {server_config.dns_server}
PrivateKey = {peer.private_key}

[Peer]
PublicKey = {server_config.public_key}
PresharedKey = {peer.preshared_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {server_config.endpoint_ip}:{server_config.endpoint_port}
PersistentKeepalive = 60
"""
