import os
import subprocess
import tempfile
from typing import Callable, Union

import wgconfig

from core.db.model_serializer import ConnectionPeer
from core.logs import core_logger


class WGHub:
    def __init__(self, path: str, is_amnezia: bool = False, auto_sync: bool = True):
        self.path = path
        self.wgconfig = wgconfig.WGConfig(path)
        self.interface_name = os.path.basename(path).split(".")[0]
        self.auto_sync = auto_sync

        core_logger.debug(f"Path to configuration file: {self.path} => Interface name: {self.interface_name}")
        self.wgconfig.read_file()
        self.change_command_mode(is_amnezia)

    @core_logger.catch()
    def sync_config(self):
        strip = subprocess.run([f"{self.command}-quick", "strip", self.path], check=True, capture_output=True, text=True)

        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(strip.stdout.encode("utf-8"))
            temp_file.flush()

            subprocess.run([self.command, "syncconf", self.interface_name, temp_file.name], check=True)

        core_logger.info("Configuration synced with Wireguard server.")

    def apply_and_sync(func: Callable):
        @core_logger.catch()
        def inner(self, peer: ConnectionPeer):
            func(self, peer)

            self.wgconfig.write_file()
            if self.auto_sync:
                self.sync_config()
                core_logger.info("Config applied and synced with Wireguard server.")
            else:
                core_logger.warning("Auto sync is disabled. Config was applied to file, consider syncing it manually.")

        return inner

    @apply_and_sync
    def add_peer(self, peer: ConnectionPeer):
        self.wgconfig.add_peer(peer.public_key, f"# {peer.peer_name}")
        self.wgconfig.add_attr(peer.public_key, "PresharedKey", peer.preshared_key)
        self.wgconfig.add_attr(peer.public_key, "AllowedIPs", peer.shared_ips + "/32")
        with core_logger.contextualize(peer=peer):
            core_logger.info("A new peer has appeared.")

    @apply_and_sync
    def enable_peer(self, peer: ConnectionPeer):
        self.wgconfig.enable_peer(peer.public_key)
        with core_logger.contextualize(peer=peer):
            core_logger.info("Peer enabled.")

    @apply_and_sync
    @core_logger.catch()
    def enable_peers(self, peers: list[ConnectionPeer]):
        for peer in peers:
            self.wgconfig.enable_peer(peer.public_key)
        with core_logger.contextualize(peers=peers):
            core_logger.info("Peers enabled.")

    @apply_and_sync
    def disable_peer(self, peer: ConnectionPeer):
        self.wgconfig.disable_peer(peer.public_key)
        with core_logger.contextualize(peer=peer):
            core_logger.info("Peer disabled.")

    @apply_and_sync
    def disable_peers(self, peers: list[ConnectionPeer]):
        for peer in peers:
            self.wgconfig.disable_peer(peer.public_key)
        with core_logger.contextualize(peers=peers):
            core_logger.info("Peers disabled.")

    @apply_and_sync
    def delete_peer(self, peer: ConnectionPeer):
        self.wgconfig.del_peer(peer.public_key)
        with core_logger.contextualize(peer=peer):
            core_logger.info("A peer has been destroyed.")

    def change_command_mode(self, is_amnezia: bool):
        """Changes command from `wg` to `awg` to be able to work with amnezia-wg

        Args:
            is_amnezia (bool): Change to amnezia or not
        """
        if is_amnezia:
            self.is_amnezia = True
            self.command = "awg"
            core_logger.info("Behaviour is set to Amnezia WG.")
        else:
            self.is_amnezia = False
            self.command = "wg"
            core_logger.info("Behaviour is set to default WG.")

def disable_server(path: str) -> bool:
    """Returns True if server was disabled successfully"""
    if not os.path.exists(path):
        return False
    core_logger.info("Disabling WG server...")
    return "error" in subprocess.getoutput(f"wg-quick down {path}")

def enable_server(path: str) -> bool:
    """Returns True if server was enabled successfully"""
    if not os.path.exists(path):
        return False
    core_logger.info("Enabling WG server...")
    return "error" in subprocess.getoutput(f"wg-quick up {path}")

def make_wg_server_base_str(ip: str, endpoint_port: Union[str, int], private_key: str) -> str:
    return f"""[Interface]
Address = {ip}.1/24
ListenPort = {endpoint_port}
PrivateKey = {private_key}

"""

def peer_to_str_wg_server(peer: ConnectionPeer) -> str:
    return f"""
# {peer.peer_name}
[Peer]
PublicKey = {peer.public_key}
PresharedKey = {peer.preshared_key}
AllowedIPs = {peer.shared_ips}/32

"""
