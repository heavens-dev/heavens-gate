import datetime
from typing import Optional, overload

from pydantic import BaseModel

from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.db.model_serializer import ConnectionPeer, User

class Client(BaseModel):
    """
    General class for operating with single client.
    All methods that perform I/O operations (transactions) **should** be used with `atomic` context manager.

    Example:
    >>> client = ClientFactory(tg_id=<telegram_id>).get_client() # -> Client
    >>> with db.atomic():
    ...    client.set_ip_address()
    """
    userdata: User
    @overload
    def delete_peer(self) -> bool: ...
    @overload
    def delete_peer(self, ip_address: str) -> bool: ...
    def add_peer(self,
                 shared_ips: str,
                 public_key: Optional[str] = None,
                 private_key: Optional[str] = None,
                 preshared_key: Optional[str] = None,
                 is_amnezia: Optional[bool] = False,
                 peer_name: str = None) -> ConnectionPeer: ...
    def get_peers(self) -> list[ConnectionPeer]: ...
    def set_ip_address(self, ip_address: str) -> bool: ...
    def set_status(self, status: ClientStatusChoices) -> bool: ...
    def set_expire_time(self, expire_date: datetime.datetime) -> bool: ...
    def change_peer_name(self, peer_id: int, peer_name: str) -> bool: ...
    def set_peer_status(self, peer_id: int, peer_status: PeerStatusChoices) -> None: ...
    def set_peer_timer(self, peer_id: int, time: datetime.datetime) -> None: ...
    def get_connected_peers(self) -> list[ConnectionPeer]: ...

class ClientFactory(BaseModel):
    """Class for creating `Client`s."""
    tg_id: Optional[int]
    def get_or_create_client(self, name: str, **kwargs) -> Client: ...

    @overload
    def get_client(self) -> Optional[Client]: ...

    @overload
    @staticmethod
    def get_client(ip_address: str) -> Optional[Client]: ...

    @staticmethod
    def select_clients() -> list[Client]: ...
    @staticmethod
    def select_peers() -> list[ConnectionPeer]: ...

    @staticmethod
    def get_peer(ip_address: str) -> Optional[ConnectionPeer]: ...

    @overload
    def delete_client(self) -> bool: ...

    @overload
    @staticmethod
    def delete_client(ip_address: str) -> bool: ...

    @staticmethod
    def count_clients() -> int: ...

    @staticmethod
    def get_latest_peer_id() -> int: ...

    @staticmethod
    def get_ip_addresses() -> list[str]: ...

    @staticmethod
    def delete_peer(peer: ConnectionPeer) -> bool: ...
