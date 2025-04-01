import re
from typing import Optional
from urllib.parse import quote

from py3xui import Api
from py3xui.client import Client

from core.db.enums import PeerStatusChoices
from core.db.model_serializer import XrayPeer
from core.logs import core_logger


class XrayWorker:
    def __init__(self,
                 host: str,
                 port: str,
                 web_path: str,
                 username: str,
                 password: str,
                 token: Optional[str] = None,
                 tls: bool = True
                 ):
        self.host = host
        self.port = port
        host = host + ':' + port + (f"/{web_path}/" if web_path else '')
        self.api = Api(host, username, password, token, use_tls_verify=tls)

        self.api.login()
        core_logger.info("Successfully logged into 3x-ui.")

    @staticmethod
    def peer_to_client(peer: XrayPeer) -> Client:
        return Client(
            id=str(peer.peer_id), # explicitly converting to string, bug in py3xui
            email=peer.peer_name,
            enable=PeerStatusChoices.xray_enabled(peer.peer_status),
            flow=peer.flow,
            inbound_id=peer.inbound_id,
        )

    def get_connection_string(self, peer: XrayPeer):
        inbound = self.api.inbound.get_by_id(peer.inbound_id)

        inbound_settings = inbound.stream_settings.reality_settings.get("settings")

        host = re.sub(r"https?://|www\.", "", self.host)
        public_key = inbound_settings.get("publicKey")
        website_name = inbound.stream_settings.reality_settings.get("serverNames")[0]
        short_id = inbound.stream_settings.reality_settings.get("shortIds")[0]
        fingerprint = inbound_settings.get("fingerprint")
        remark = quote(inbound.remark)
        peer_name = quote(peer.peer_name)

        return (f"vless://{peer.peer_id}@{host}:{inbound.port}"
                f"?type=tcp&security=reality&pbk={public_key}&fp={fingerprint}"
                f"&sni={website_name}&sid={short_id}&spx=%2F&flow={peer.flow}#{remark}-{peer_name}"
                )

    @core_logger.catch()
    def add_peers(self, inbound_id: int, peers: list[XrayPeer]) -> None:
        """Adds a peer to the 3x-ui API"""
        clients = []

        for peer in peers:
            if peer.inbound_id != inbound_id:
                with core_logger.contextualize(peer_id=peer.peer_id):
                    core_logger.warning(
                        f"Inbound ID does not match the peer's inbound ID: {peer.inbound_id} != {inbound_id}"
                    )
            clients.append(self.peer_to_client(peer))

        self.api.client.add(inbound_id, clients)

        with core_logger.contextualize(xray_peers=peers):
            core_logger.info(f"Added new Xray peers.")

    @core_logger.catch()
    def update_peer(self, peer: XrayPeer) -> None:
        client = self.peer_to_client(peer)
        self.api.client.update(client.id, client)

        with core_logger.contextualize(xray_peer=peer):
            core_logger.info(f"Updated Xray peer.")

    @core_logger.catch()
    def delete_peer(self, peer: XrayPeer) -> None:
        client = self.peer_to_client(peer)
        self.api.client.delete(client.inbound_id, client.id)

        with core_logger.contextualize(xray_peer=peer):
            core_logger.info(f"Deleted Xray peer.")

    @core_logger.catch()
    def is_connected(self, peer: XrayPeer) -> bool:
        # because `api.client.online()` returns a list of strings
        # there is may be a problem when user has changed his name
        # FIXME later
        online_clients = self.api.client.online()
        for client in online_clients:
            if client == peer.peer_name:
                return True
        core_logger.debug(f"Peer {peer.peer_name} is not connected, online clients: {online_clients}.")
        return False

    @core_logger.catch()
    def enable_peer(self, peer: XrayPeer) -> None:
        peer.enable = True
        self.api.client.update(peer.peer_id, self.peer_to_client(peer))

    @core_logger.catch()
    def disable_peer(self, peer: XrayPeer):
        peer.enable = False
        self.api.client.update(peer.peer_id, self.peer_to_client(peer))

    # TODO list:
    # [ ] edit peers
    # [ ] delete peers
    # [ ] get peers
    # [ ] ensure login
    # [x] enable peer
    # [x] disable peer
    # [x] is connected
