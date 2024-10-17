import subprocess
from typing import Union

from core.db.model_serializer import ConnectionPeer


def disable_server(path: str) -> bool:
    """Returns True if server was disabled successfully"""
    return "error" in subprocess.getoutput(f"wg-quick down {path}")

def enable_server(path: str) -> bool:
    """Returns True if server was enabled successfully"""
    return "error" in subprocess.getoutput(f"wg-quick up {path}")

def make_wg_server_base_str(ip: str, endpoint_port: Union[str, int], private_key: str) -> str:
    return f"""[Interface]
Address = {ip}.1/24
ListenPort = {endpoint_port}
PrivateKey = {private_key}

"""

def peer_to_str_wg_server(peer: ConnectionPeer):
        return f"""
#{peer.peer_name}
[Peer]
PublicKey = {peer.public_key}
PresharedKey = {peer.preshared_key}
AllowedIPs = {peer.shared_ips}/32

"""
