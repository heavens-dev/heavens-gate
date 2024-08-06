from typing import overload


class Client:
    """
    General class for operating with single client. 
    All methods that perform I/O operations **should** be used with `atomic` context manager.

    Example:
        >>> client = Client(tg_id=<telegram_id>)
        >>> with db.atomic():
        ...    client.create_client()
    """
    @overload
    def delete_client(self) -> bool: ...
    @overload
    def delete_client(self, ip_address: str) -> bool: ...
    @overload
    def delete_peer(self) -> bool: ...
    @overload
    def delete_peer(self, ip_address: str) -> bool: ...

class Users:
    """
    Class for working with multiple users at the same time for implementing something...

    _**NaStY**_
    """
