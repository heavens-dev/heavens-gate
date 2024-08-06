from core.db.models import UserModel, ConnectionPeerModel
from pydantic import BaseModel, ConfigDict
from core.db.model_serializer import User
from multimethod import multimethod


class Client(BaseModel):
    model_config = ConfigDict(ignored_types=(multimethod, ))

    tg_id: int

    def is_registered(self) -> bool:
        """Checks if current user is in DB.

        Returns:
            bool: True if user is in DB. False otherwise.
        """
        return UserModel.select().where(UserModel.telegram_id == self.tg_id).count() == 1

    @multimethod
    def delete_client(self) -> bool:
        return UserModel.delete().where(UserModel.telegram_id == self.tg_id).execute() == 1

    @multimethod
    def delete_client(self, ip_address: str) -> bool:
        return UserModel.delete().where(UserModel.ip_address == ip_address).execute() == 1

    def get_client_model(self) -> UserModel:
        return UserModel.get(UserModel.telegram_id == self.tg_id)

    def get_client(self) -> User:
        return User.model_validate(self.get_client_model())

    def update_client(self, **kwargs):
        """Updates a user in database. Not ConnectionPeer

        Args:
            kwargs: DB fields
        Returns:
            True if operation was successfull. False otherwise.
        """
        return UserModel.update(**kwargs).where(UserModel.telegram_id == self.tg_id).execute() == 1

    def create_client(self, name: str, **kwargs) -> UserModel:
        return UserModel.create(telegram_id=self.tg_id, name=name, **kwargs)

    def add_peer(self, public_key: str, preshared_key: str, shared_ips: str):
        client = self.get_client_model()
        return ConnectionPeerModel.create(
            user=client,
            public_key=public_key,
            preshared_key=preshared_key,
            shared_ips=shared_ips
        )

    def get_peers(self) -> list[ConnectionPeerModel]:
        client = self.get_client_model()
        return list(ConnectionPeerModel.select().where(ConnectionPeerModel.user == client))

    @multimethod
    def delete_peer(self) -> bool:
        """Delete peers by `telegram_id`

        Returns:
            bool: True if successfull. False otherwise
        """
        return ConnectionPeerModel.delete().where(UserModel.telegram_id == self.tg_id).execute() == 1

    @multimethod
    def delete_peer(self, ip_address: str) -> bool:
        peers = self.get_peers()
        for peer in peers:
            if ip_address in peer.shared_ips:
                return ConnectionPeerModel.delete().where(ConnectionPeerModel.shared_ips == ip_address).execute() == 1
        return False

    class Meta:
        arbitrary_types_allowed=True


class Users:
    @staticmethod
    def get_users() -> list[User]:
        return [User.model_validate(i) for i in UserModel.select()]
