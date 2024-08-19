import subprocess
from core.db.model_serializer import ConnectionPeer
from config.settings import Server
from config.loader import server_cfg
from core.wg.keygen import private_key, preshared_key, public_key
import os

#Here also would be good server class, but there's no one, only config class
def setup_peer_keys(peer: ConnectionPeer) -> str:
    peer_private_key = private_key()
    peer.privatekey = peer_private_key
    peer.public_key = public_key(peer_private_key)
    peer.preshared_key = preshared_key()
    

def setup_server_keys(server: Server):
    server_private_key = private_key()
    server_public_key = public_key(server_private_key)
    server.privatekey = server_private_key
    server.public_key = server_public_key

def create_server_base(server: Server):
    return f"""[Interface]
Address = {server.user_ip}.1/24
ListenPort = {server.endpoint_port}
PrivateKey = {server.private_key}
"""

def peer_for_server_config(peer: ConnectionPeer) -> str:
    return f"""
#{peer.peer_name}
[Peer]
PublicKey = {peer.public_key}
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

