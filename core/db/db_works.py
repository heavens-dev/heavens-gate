from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, PrivateAttr
from multimethod import multimethod
from peewee import DoesNotExist
from core.db.models import UserModel, ConnectionPeerModel
from core.db.model_serializer import User
from core.db.enums import StatusChoices


class Client(BaseModel):
    model_config = ConfigDict(ignored_types=(multimethod, ))

    userdata: User
    __model: UserModel = PrivateAttr(init=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "model" not in kwargs.keys():
            raise AttributeError("model attribute was not found in kwargs.")
        self.__model = kwargs["model"]

    def __update_client(self, **kwargs) -> bool:
        """Updates a user in database. Not ConnectionPeer

        Args:
            kwargs: DB fields
        Returns:
            True if operation was successfull. False otherwise.
        """
        return (self.__model.update(**kwargs)
                .where(UserModel.telegram_id == self.userdata.telegram_id)
                .execute()) == 1

    def set_ip_address(self, ip_address: str) -> bool:
        self.userdata.ip_address = ip_address
        return self.__update_client(ip_address=ip_address)
    
    def set_status(self, status: StatusChoices) -> bool:
        self.userdata.status = status
        return self.__update_client(status=status.value)

    def add_peer(self, public_key: str, preshared_key: str, shared_ips: str):
        return ConnectionPeerModel.create(
            user=self.__model,
            public_key=public_key,
            preshared_key=preshared_key,
            shared_ips=shared_ips
        )

    def get_peers(self) -> list[ConnectionPeerModel]:
        return list(ConnectionPeerModel.select()
                    .where(ConnectionPeerModel.user == self.__model))

    @multimethod
    def delete_peer(self) -> bool:
        """Delete peers by `telegram_id`

        Returns:
            bool: True if successfull. False otherwise
        """
        return (ConnectionPeerModel.delete()
                .where(UserModel.telegram_id == self.userdata.telegram_id)
                .execute()) == 1

    @multimethod
    def delete_peer(self, ip_address: str) -> bool:
        """Delete single peer by `ip_address`

        Returns:
            bool: True if successfull. False otherwise
        """
        peers = self.get_peers()
        for peer in peers:
            if ip_address in peer.shared_ips:
                return (ConnectionPeerModel.delete()
                        .where(ConnectionPeerModel.shared_ips == ip_address)
                        .execute()) == 1
        return False

    class Meta:
        arbitrary_types_allowed=True

class ClientFactory(BaseModel):
    model_config = ConfigDict(ignored_types=(multimethod, ))

    tg_id: int

    def get_or_create_client(self, name: str, **kwargs) -> Client:
        """Retrieves or creates a record of the user in the database.
        Use this method when you're unsure whether the user already exists in the database or not."""
        model = UserModel.get_or_create(telegram_id=self.tg_id, name=name, **kwargs)[0]
        return Client(model=model, userdata=User.model_validate(model))

    @multimethod
    def get_client(self) -> Optional[Client]:
        try:
            model = UserModel.get(UserModel.telegram_id == self.tg_id)
            return Client(model=model, userdata=User.model_validate(model))
        except DoesNotExist:
            return None
    
    @multimethod
    @staticmethod
    def get_client(ip_address: str) -> Optional[Client]:
        model = UserModel.select().where(UserModel.ip_address == ip_address)
        if not model:
            return None
        return Client(model=model, userdata=User.model_validate(model))

    @staticmethod
    def select_clients() -> list[Client]:
        return [Client(model=i, userdata=User.model_validate(i)) for i in UserModel.select()]
    
    @multimethod
    @staticmethod
    def delete_client(ip_address: str) -> bool:
        return UserModel.delete().where(UserModel.ip_address.contains(ip_address)).execute() == 1

    @multimethod
    def delete_client(self) -> bool:
        return UserModel.delete_by_id(self.tg_id)
    
    @staticmethod
    def count_clients() -> int:
        return UserModel.select().count()

    class Meta:
        arbitrary_types_allowed=True

