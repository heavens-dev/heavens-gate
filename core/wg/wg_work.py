import subprocess
from core.db.model_serializer import ConnectionPeer
from config.loader import server_cfg
from core.wg.keygen import private_key, preshared_key, public_key
import os

def setup_peer_keys(peer: ConnectionPeer) -> str:
    peer_private_key = private_key()
    peer.privatekey = peer_private_key
    peer.public_key = public_key(peer_private_key)
    peer.preshared_key = preshared_key()
    

def setup_server_keys():
    server_private_key = private_key()
    server_public_key = public_key(server_private_key)
    server_cfg.privatekey = server_private_key
    server_cfg.public_key = server_public_key
    print(server_cfg.public_key)

def create_server_base():
    return f"""[Interface]
Address = {server.server_ip}/24
ListenPort = {server.endpoint_port}
PrivateKey = {server.privatekey}
"""

def peer_for_server_config(peer: ConnectionPeer) -> str:
    return f"""[Peer]
PublicKey = {peer.publickey}
PresharedKey = {peer.preshared_key}
AllowedIPs = {peer.shared_ips}/32
"""

def disable_server(path):
    if "error" in subprocess.getoutput(f"wg-quick down {path}"):
        return 0
    else:
        return 1

def enable_server(path):
    if "error" in subprocess.getoutput(f"wg-quick up {path}"):
        return 0
    else:
        return 1

def create_server_config(config):
    #Change name on the normal one when testing will end
    wg_file = open("wghub_test.conf", "w")
    wg_file.write(config)
    wg_file.close()
    return os.path.abspath("wghub_test.conf")

