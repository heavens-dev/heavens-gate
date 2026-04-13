import asyncio
import atexit
import datetime
import re
import secrets
import threading
from typing import Optional
from urllib.parse import quote

from py3xui import Api
from py3xui.client import Client
from remnawave import RemnawaveSDK
from remnawave.exceptions import NotFoundError
from remnawave.models import (CreateUserRequestDto,
                              GetSubscriptionByUUIDResponseDto,
                              UpdateUserRequestDto)
from requests.exceptions import JSONDecodeError

from core.db.enums import PeerStatusChoices
from core.db.model_serializer import User, XrayPeer
from core.db.serializer_extensions import SerializerExtensions
from core.logs import core_logger
from core.utils.uuid_utils import generate_deterministic_uuid_string
from core.xray.remnawave_enums import remnawave_squads_list


class XrayWorker:
    def __init__(
            self,
            host: str,
            port: str,
            web_path: str,
            username: str,
            password: str,
            token: Optional[str] = None,
            tls: bool = True,
            sub_domain: Optional[str] = None,
            sub_port: Optional[int] = None,
            sub_path: Optional[str] = None,
            remnawave_token: Optional[str] = None,
            remnawave_base_url: Optional[str] = None
        ):
        self.host = host
        self.port = port
        host = host + ':' + port + (f"/{web_path}/" if web_path else '')
        self.api = Api(host, username, password, token, use_tls_verify=tls)

        self.sub_domain = sub_domain
        self.sub_port = sub_port
        self.sub_path = sub_path

        self.sub_host = f"{self.sub_domain}:{self.sub_port}/{self.sub_path}"
        self.remnawave = None
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_loop_thread: Optional[threading.Thread] = None
        self._async_loop_ready = threading.Event()
        self._async_loop_lock = threading.Lock()
        atexit.register(self._stop_async_loop)

        if not self.__login():
            raise ValueError("Failed to login to 3x-ui API. Check your credentials.")

        if remnawave_token and remnawave_base_url:
            self.__remnawave_login(remnawave_token, remnawave_base_url)
            core_logger.info("Successfully authenticated with Remnawave.")

        core_logger.info("Successfully logged into 3x-ui.")

    @staticmethod
    def generate_subscription_token() -> str:
        return secrets.token_urlsafe(8)

    def _run_async(self, coro):
        self._ensure_async_loop()
        if self._async_loop is None:
            raise RuntimeError("Background async loop is not initialized.")

        return asyncio.run_coroutine_threadsafe(coro, self._async_loop).result()

    def _ensure_async_loop(self) -> None:
        loop = self._async_loop
        if loop is not None and loop.is_running() and not loop.is_closed():
            return

        with self._async_loop_lock:
            loop = self._async_loop
            if loop is not None and loop.is_running() and not loop.is_closed():
                return

            self._async_loop_ready.clear()

            def loop_runner() -> None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._async_loop = loop
                self._async_loop_ready.set()

                loop.run_forever()

                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

                loop.close()

            self._async_loop_thread = threading.Thread(
                target=loop_runner,
                daemon=True,
                name="xray-worker-async-loop"
            )
            self._async_loop_thread.start()

        if not self._async_loop_ready.wait(timeout=5):
            raise RuntimeError("Failed to start background async loop.")

    def _stop_async_loop(self) -> None:
        loop = self._async_loop
        if loop is None or loop.is_closed() or not loop.is_running():
            return

        loop.call_soon_threadsafe(loop.stop)

    def get_subscription_link(self, sub_token: str) -> str:
        return f"{self.sub_host}/{sub_token}"

    def remnawave_get_subscription_link(self, user: User) -> str:
        try:
            sub: GetSubscriptionByUUIDResponseDto = self._run_async(self.remnawave.subscriptions.get_subscription_by_uuid(
                uuid=generate_deterministic_uuid_string(user.user_id)
            ))
            return sub.subscription_url
        except Exception as e:
            core_logger.error(f"Failed to get subscription with Remnawave: {e}")
            return None

    def __remnawave_login(self, token: str, base_url: str) -> None:
        try:
            self.remnawave = RemnawaveSDK(token=token, base_url=base_url)
        except Exception as e:
            core_logger.error(f"Failed to authenticate with Remnawave: {e}")
            return None

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
            core_logger.error(f"Failed to login to 3x-ui: {e}")
            return False
        return True

    @staticmethod
    def peer_to_client(peer: XrayPeer, needs_user_fields: bool = False) -> Client:
        """
        Convert an XrayPeer object to a Client object.

        This static method transforms an XrayPeer instance into a XRay Client instance,
        mapping the appropriate fields between the two models.

        Note:
            `needs_user_fields` should be used when the resulting `Client` object requires user-related fields such as `expiry_time` and `sub_id` and `Client` object will be used for update API calls.
            The thing is that missing fields will be assumed to be `None`, and on update API call these `None` values **will overwrite existing values** in the API,\
            which can lead to unintended consequences (like removing expiry time or subscription ID from a peer that previously had it).

        Args:
            peer (XrayPeer): The XrayPeer object to convert.
            needs_user_fields (bool): Flag indicating whether to include user-related fields

        Returns:
            Client: A newly created Client object with properties derived from the XrayPeer and optionally its related user data.
        """
        if needs_user_fields:
            user = SerializerExtensions.get_user_from_peer(peer)
            core_logger.debug(f"Converting XrayPeer to Client. Peer: {peer}, Resolved User: {user}")
            if not user:
                raise ValueError(f"Failed to resolve user for peer {peer.peer_id} with user_id {peer.user_id}. Cannot convert to Client without user data.")

            return Client(
                id=str(peer.hash_id),
                email=peer.name,
                enable=PeerStatusChoices.xray_enabled(peer.status),
                flow=peer.flow,
                inbound_id=peer.inbound_id,
                # int(expiry_time.timestamp() * 1000)
                expiry_time=int(user.subscription_expiry.timestamp() * 1000) if user.subscription_expiry else None,
                sub_id=user.vless_sub_token
            )

        return Client(
            id=str(peer.hash_id), # explicitly converting to string
            email=peer.name,
            enable=PeerStatusChoices.xray_enabled(peer.status),
            flow=peer.flow,
            inbound_id=peer.inbound_id,
        )

    def get_connection_string(self, peer: XrayPeer):
        inbound = self.api.inbound.get_by_id(peer.inbound_id)

        inbound_reality_settings: dict = inbound.stream_settings.reality_settings.get("settings")
        inbound_external_proxy: list = inbound.stream_settings.external_proxy

        if inbound_external_proxy:
            inbound_external_proxy_settings: dict = inbound_external_proxy[0]
            host = inbound_external_proxy_settings.get("dest")
        else:
            host = re.sub(r"https?://|www\.", "", self.host)

        public_key = inbound_reality_settings.get("publicKey")
        website_name = inbound.stream_settings.reality_settings.get("serverNames")[0]
        short_id = inbound.stream_settings.reality_settings.get("shortIds")[0]
        fingerprint = inbound_reality_settings.get("fingerprint")
        remark = quote(inbound.remark)
        peer_name = quote(peer.name)

        return (
            f"vless://{peer.hash_id}@{host}:{inbound.port}"
            f"?type=tcp&security=reality&pbk={public_key}&fp={fingerprint}"
            f"&sni={website_name}&sid={short_id}&spx=%2F&flow={peer.flow}#{remark}-{peer_name}"
        )

    @core_logger.catch()
    def add_peers(
        self,
        inbound_id: int,
        peers: list[XrayPeer],
        expiry_time: Optional[datetime.datetime] = None,
        sub_token: Optional[str] = None
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
            sub_token (str, optional): Subscription token for VLESS protocol. Defaults to None.
        """
        clients: list[Client] = []

        for peer in peers:
            if peer.inbound_id != inbound_id:
                with core_logger.contextualize(peer_id=peer.peer_id):
                    core_logger.warning(
                        f"Given inbound ID does not match the peer's inbound ID: {peer.inbound_id} != {inbound_id}"
                    )
            client = self.peer_to_client(peer)
            if expiry_time is not None:
                client.expiry_time = int(expiry_time.timestamp() * 1000)
            if sub_token is not None:
                client.sub_id = sub_token
            clients.append(client)

        self.api.client.add(inbound_id, clients)

        with core_logger.contextualize(xray_peers=peers):
            core_logger.info(f"Added new Xray peers.")

    @core_logger.catch()
    def update_peer(
        self,
        peer: XrayPeer,
        expiry_time: Optional[datetime.datetime] = None,
        vless_sub_token: Optional[str] = None
    ) -> None:
        """
        Update an Xray peer in the API and optionally set its expiry time.
        """
        client = self.peer_to_client(peer, True)

        if expiry_time is not None:
            client.expiry_time = int(expiry_time.timestamp() * 1000)
        if vless_sub_token is not None:
            client.sub_id = vless_sub_token
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
                if client == peer.name:
                    return True
            core_logger.debug(f"Peer {peer.name} is not connected, online clients: {online_clients}.")
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
    def enable_peer(self, peer: XrayPeer, expire_time: Optional[datetime.datetime] = None) -> None:
        client = self.peer_to_client(peer, True)
        client.enable = True
        if expire_time is not None:
            client.expiry_time = int(expire_time.timestamp() * 1000)
        self.api.client.update(client.id, client)

    @core_logger.catch()
    def disable_peer(self, peer: XrayPeer, expire_time: Optional[datetime.datetime] = None) -> None:
        client = self.peer_to_client(peer, True)
        client.enable = False
        if expire_time is not None:
            client.expiry_time = int(expire_time.timestamp() * 1000)
        self.api.client.update(client.id, client)

    def remnawave_verify_users(self, users: list[User]) -> Optional[int]:
        """
        Verify that the given users exist in Remnawave, and create them if they don't.

        Args:
            users (list[User]): List of User objects to verify in Remnawave.

        Returns:
            int: Number of newly created users.
        """
        new_users_count = 0
        for user in users:
            try:
                self._run_async(self.remnawave.users.get_user_by_uuid(
                    generate_deterministic_uuid_string(str(user.user_id)))
                )
            except NotFoundError:
                core_logger.warning(
                    f"User {user.user_id} not found in Remnawave during verification. Attempting to create."
                )
                if self.remnawave_create_user(user):
                    new_users_count += 1
        return new_users_count

    def remnawave_create_user(self, userdata: User) -> bool:
        try:
            self._run_async(self.remnawave.users.create_user(
                CreateUserRequestDto(
                    username=userdata.name,
                    expire_at=userdata.subscription_expiry or datetime.datetime.now(),
                    uuid=generate_deterministic_uuid_string(str(userdata.user_id)),
                    active_internal_squads=remnawave_squads_list(userdata.subscription_type)
                )
            ))
            core_logger.info(f"Successfully created user {userdata.user_id} in Remnawave.")
            return True
        except Exception as e:
            core_logger.error(f"Failed to create user in Remnawave: {e}")
            return False

    def remnawave_update_user(self, user: User, **kwargs) -> bool:
        """Update a user in Remnawave with given kwargs.
        As refernce to what can be updated - see `UpdateUserRequestDto` in Remnawave SDK.

        Args:
            user (User): The user whose Remnawave record should be updated.
            **kwargs: Arbitrary keyword arguments corresponding to fields in `UpdateUserRequestDto` that should be updated for the user.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        try:
            self._run_async(self.remnawave.users.update_user(
                UpdateUserRequestDto(
                    uuid=generate_deterministic_uuid_string(str(user.user_id)),
                    **kwargs
                )
            ))
            core_logger.info(f"Successfully updated user {user.user_id} in Remnawave with data: {kwargs}.")
            return True
        except Exception as e:
            core_logger.error(f"Failed to update user in Remnawave: {e}")
            return False
