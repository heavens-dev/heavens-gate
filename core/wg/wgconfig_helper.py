from core.db.model_serializer import ConnectionPeer
from config.loader import server_cfg


def get_peer_config_str(peer: ConnectionPeer) -> str:
    return f"""[Interface]
Address={server_cfg.user_ip}.{peer.id}/24
DNS=1.1.1.1
PrivateKey={server_cfg.private_key}

[Peer]
PublicKey={peer.public_key}
PresharedKey={peer.preshared_key}
AllowedIPs=0.0.0.0/0
Endpoint={server_cfg.endpoint_ip}
"""
