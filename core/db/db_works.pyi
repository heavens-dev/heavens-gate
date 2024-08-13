from typing import Optional, overload
from core.db.models import ConnectionPeerModel
from core.db.model_serializer import ConnectionPeer, User
from core.db.enums import StatusChoices
from pydantic import BaseModel


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
    def add_peer(self, public_key: str, preshared_key: str, shared_ips: str, peer_name: str = None) -> ConnectionPeer: ...
    def get_peers(self) -> list[ConnectionPeerModel]: ...
    def set_ip_address(self, ip_address: str) -> bool: ...
    def set_status(self, status: StatusChoices) -> bool: ...
    def change_peer_name(self, peer_id: int, peer_name: str) -> bool: ...

class ClientFactory(BaseModel):
    """Class for creating `Client`s."""
    tg_id: Optional[int]
    def create_client(self, name: str, **kwargs) -> "Client": ...
    
    @overload
    def get_client(self) -> Optional[Client]: ...
    
    @overload
    @staticmethod
    def get_client(ip_address: str) -> Optional[Client]: ...
    
    @staticmethod
    def select_clients() -> list["Client"]: ...
    
    @overload
    def delete_client(self) -> bool: ...
    
    @overload
    @staticmethod
    def delete_client(ip_address: str) -> bool: ...

    @staticmethod
    def count_clients() -> int: ...
