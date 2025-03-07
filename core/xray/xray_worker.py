from typing import Optional

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
        host = host + ':' + port + (f"/{web_path}/" if web_path else '')
        self.api = Api(host, username, password, token, use_tls_verify=tls)

        self.api.login()

    @core_logger.catch()
    def add_peers(self, peers: list[XrayPeer]):
        """Adds a peer to the 3x-ui API"""
        clients = []

        for peer in peers:
            clients.append(Client(
                id=peer.id,
                email=peer.peer_name,
                enable=PeerStatusChoices.xray_enabled(peer.peer_status),
                flow=peer.flow,
                inboundId=peer.inbound_id,
            ))

        self.api.client.add(peers.inbound_id, clients)

        with core_logger.contextualize(xray_peers=peers):
            core_logger.info(f"Added Xray peers {peers.peer_name}.")

    # TODO list:
    # [] edit peers
    # [] delete peers
    # [] get peers
    # [] ensure login
    # [] disable peers
