import subprocess
from core.db.model_serializer import ConnectionPeer
from config.loader import server_cfg
from core.wg.keygen import private_key, preshared_key, public_key

def create_peer_keys():
    pass

def setup_server_keys():
    server_private_key = private_key()
    server_cfg.privatekey = server_private_key
    print(f"{server_cfg.privatekey}")

def create_server_base():
    pass

def add_peer():
    pass

def delete_peer():
    pass

def disable_server():
    pass

def enable_server():
    pass

