from typing import overload


class Client:
    @overload
    def delete_client(self) -> bool: ...
    @overload
    def delete_client(self, ip_address: str) -> bool: ...
    @overload
    def delete_peer(self) -> bool: ...
    @overload
    def delete_peer(self, ip_address: str) -> bool: ...