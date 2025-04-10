from config.settings import Config
from core.wg.wgconfig_helper import get_peer_config_str


def test_get_peer_config_str(default_peers, wireguard_server_config: Config.WireguardServer):
    peer = default_peers["iamuser_0"]
    assert get_peer_config_str(wireguard_server_config, peer) == f"""[Interface]
Address = {peer.shared_ips}/{wireguard_server_config.user_ip_mask}
DNS = {wireguard_server_config.dns_server}
PrivateKey = {peer.private_key}

[Peer]
PublicKey = {wireguard_server_config.public_key}
PresharedKey = {peer.preshared_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {wireguard_server_config.endpoint_ip}:{wireguard_server_config.endpoint_port}
PersistentKeepalive = 60
"""
