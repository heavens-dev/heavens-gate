import datetime
import re
from typing import Optional
from urllib.parse import quote

from py3xui import Api
from py3xui.client import Client
from requests.exceptions import JSONDecodeError

from core.db.enums import PeerStatusChoices
from core.db.model_serializer import XrayPeer
from core.logs import core_logger


class XrayWorker:
    def __init__(
            self,
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

        if not self.__login():
            raise ValueError("Failed to login to 3x-ui API. Check your credentials.")

        core_logger.info("Successfully logged into 3x-ui.")

    def __login(self) -> bool:
        """
        Attempt to login to the 3x-ui API.

        Returns:
            bool: True if login is successful, False otherwise.

        Raises:
            ValueError: If the login fails, typically due to invalid credentials.
        """
        try:
            self.api.login()
        except ValueError as e: # typically raised when login fails due to invalid credentials
            return False
        return True

    @staticmethod
    def peer_to_client(peer: XrayPeer) -> Client:
        """
        Convert an XrayPeer object to a Client object.

        This static method transforms an XrayPeer instance into a XRay Client instance,
        mapping the appropriate fields between the two models.

        Args:
            peer (XrayPeer): The XrayPeer object to convert.

        Returns:
            Client: A newly created Client object with properties derived from the XrayPeer.
        """
        # TODO: pass an expiryTime argument to Client object somehow
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

        return (
            f"vless://{peer.peer_id}@{host}:{inbound.port}"
            f"?type=tcp&security=reality&pbk={public_key}&fp={fingerprint}"
            f"&sni={website_name}&sid={short_id}&spx=%2F&flow={peer.flow}#{remark}-{peer_name}"
        )

    @core_logger.catch()
    def add_peers(
        self, inbound_id: int, peers: list[XrayPeer], expiry_time: Optional[datetime.datetime] = None
    ) -> None:
        """
        Add XRay peers to a specified inbound.
        This method converts a list of XrayPeer objects to clients and adds them to the
        specified inbound using the XRay API. It validates that each peer's inbound_id
        matches the specified inbound_id and logs any discrepancies.

        Args:
            inbound_id (int): The ID of the inbound to add peers to.
            peers (list[XrayPeer]): List of peer objects to be added.
            expiry_time (datetime.datetime, optional): Expiration time for the peers. Defaults to None.
        """
        clients = []

        for peer in peers:
            if peer.inbound_id != inbound_id:
                with core_logger.contextualize(peer_id=peer.peer_id):
                    core_logger.warning(
                        f"Inbound ID does not match the peer's inbound ID: {peer.inbound_id} != {inbound_id}"
                    )
            client = self.peer_to_client(peer)
            if expiry_time is not None:
                client.expiry_time = int(expiry_time.timestamp() * 1000)
            clients.append(client)

        self.api.client.add(inbound_id, clients)

        with core_logger.contextualize(xray_peers=peers):
            core_logger.info(f"Added new Xray peers.")

    @core_logger.catch()
    def update_peer(self, peer: XrayPeer, expiry_time: datetime.datetime = None) -> None:
        """
        Update an Xray peer in the API and optionally set its expiry time.
        """
        client = self.peer_to_client(peer)

        if expiry_time is not None:
            client.expiry_time = int(expiry_time.timestamp() * 1000)
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
        try:
            online_clients = self.api.client.online()
            for client in online_clients:
                if client == peer.peer_name:
                    return True
            core_logger.debug(f"Peer {peer.peer_name} is not connected, online clients: {online_clients}.")
            return False
        except JSONDecodeError:
            # so, here 3x-ui API probably returned an empty response ( {} )
            # which means that our token should be expired
            # py3xui does not handle this case, so we need to do it ourselves
            core_logger.error("Failed to decode JSON response from the API. Probably token expired, trying to re-login.")

            if not self.__login():
                core_logger.error("Failed to re-login to the 3x-ui API after token expiration.")

            return False

    @core_logger.catch()
    def enable_peer(self, peer: XrayPeer) -> None:
        client = self.peer_to_client(peer)
        client.enable = True
        self.api.client.update(peer.peer_id, client)

    @core_logger.catch()
    def disable_peer(self, peer: XrayPeer):
        client = self.peer_to_client(peer)
        client.enable = False
        self.api.client.update(peer.peer_id, client)
