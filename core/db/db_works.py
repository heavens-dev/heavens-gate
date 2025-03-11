import datetime
import random
from typing import Optional

from multimethod import multimethod
from peewee import SQL, DoesNotExist
from pydantic import BaseModel, ConfigDict, PrivateAttr

from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.db.model_serializer import ConnectionPeer, User
from core.db.models import ConnectionPeerModel, UserModel
from core.logs import core_logger
from core.wg.keygen import (generate_preshared_key, generate_private_key,
                            generate_public_key)


class Client(BaseModel):
    model_config = ConfigDict(ignored_types=(multimethod, ))

    userdata: User
    __model: UserModel = PrivateAttr(init=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "model" not in kwargs.keys():
            raise AttributeError("model attribute was not found in kwargs.")
        self.__model = kwargs["model"]

    @core_logger.catch()
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

    @core_logger.catch()
    def __update_peer(self, peer_id: int, **kwargs) -> bool:
        """Updates a ConnectionPeer by peer id.

        Args:
            kwargs: DB fields
        Returns:
            True if operation was successfull. False otherwise.
        """
        return (ConnectionPeerModel.update(**kwargs)
                .where(ConnectionPeerModel.id == peer_id)
                .execute()) == 1

    def set_ip_address(self, ip_address: str) -> bool:
        self.userdata.ip_address = ip_address
        result = self.__update_client(ip_address=ip_address)
        with core_logger.contextualize(ip_address=ip_address, result=result):
            core_logger.info(f"Tried to change IP address.")
        return result

    def set_status(self, status: ClientStatusChoices) -> bool:
        self.userdata.status = status
        return self.__update_client(status=status.value)

    def set_expire_time(self, expire_time: datetime.datetime) -> bool:
        self.userdata.expire_time = expire_time
        return self.__update_client(expire_time=expire_time)

    @core_logger.catch()
    def add_peer(self,
                 shared_ips: str,
                 public_key: Optional[str] = None,
                 private_key: Optional[str] = None,
                 preshared_key: Optional[str] = None,
                 is_amnezia: Optional[bool] = False,
                 peer_name: str = None) -> ConnectionPeer:
        """
        Adds peer to database. Automatically generates peer keys if they're not present in arguments.

        Returns `ConnectionPeer`.
        """
        private_peer_key = private_key or generate_private_key(is_amnezia=is_amnezia)
        public_peer_key = public_key or generate_public_key(private_peer_key, is_amnezia=is_amnezia)
        preshared_peer_key = preshared_key or generate_preshared_key(is_amnezia=is_amnezia)
        Jc, Jmin, Jmax = None, None, None
        if is_amnezia:
            # ? recommended values for: -- [3, 10], Jmin = 50, Jmax = 1000
            # ? so they can be changed, but we'll see
            Jc = random.randint(3, 127)
            Jmin = random.randint(3, 700)
            Jmax = random.randint(Jmin + 1, 1270)
        peer = ConnectionPeer.model_validate(ConnectionPeerModel.create(
            user=self.__model,
            public_key=public_peer_key,
            private_key=private_peer_key,
            preshared_key=preshared_peer_key,
            shared_ips=shared_ips,
            peer_name=peer_name,
            is_amnezia=is_amnezia,
            Jc=Jc,
            Jmin=Jmin,
            Jmax=Jmax,
        ))
        with core_logger.contextualize(peer=peer):
            core_logger.info(f"New peer was created.")
        return peer

    def __get_peers(self, *criteria) -> list[ConnectionPeerModel]:
        """Private method for working with peers"""
        return list(ConnectionPeerModel.select()
                    .where(ConnectionPeerModel.user == self.__model, *criteria))

    @core_logger.catch()
    def get_peers(self) -> list[ConnectionPeer]:
        """Get validated peers model(s)"""
        return [
            ConnectionPeer.model_validate(model)
            for model in self.__get_peers()
        ]

    @core_logger.catch()
    def change_peer_name(self, peer_id: int, peer_name: str) -> bool:
        result = self.__update_peer(peer_id, peer_name=peer_name)
        with core_logger.contextualize(peer_id=peer_id, result=result):
            core_logger.info(f"Tried to change Peer name to {peer_name}")
        return result

    @core_logger.catch()
    def set_peer_status(self, peer_id: int, peer_status: PeerStatusChoices) -> bool:
        result = self.__update_peer(peer_id, peer_status=peer_status.value)
        with core_logger.contextualize(peer_id=peer_id, result=result):
            core_logger.debug(f"Tried to change peer status to {peer_status}")
        return result

    @core_logger.catch()
    def set_peer_timer(self, peer_id, time: datetime.datetime) -> bool:
        result = self.__update_peer(peer_id, peer_timer=time)
        with core_logger.contextualize(peer_id=peer_id, result=result):
            core_logger.debug(f"Tried to change peer timer to {time}")
        return result

    @core_logger.catch()
    def get_connected_peers(self) -> list[ConnectionPeer]:
        return [
            ConnectionPeer.model_validate(model)
            for model in self.__get_peers(ConnectionPeerModel.peer_status == PeerStatusChoices.STATUS_CONNECTED.value)
        ]

    @multimethod
    @core_logger.catch()
    def delete_peer(self) -> bool:
        """Delete peers by `telegram_id`

        Returns:
            bool: True if successfull. False otherwise
        """
        core_logger.info(f"Deleted all peers for user {self.userdata.telegram_id}")
        return (ConnectionPeerModel.delete()
                .where(UserModel.telegram_id == self.userdata.telegram_id)
                .execute()) == 1

    @multimethod
    @core_logger.catch()
    def delete_peer(self, ip_address: str) -> bool:
        """Delete single peer by `ip_address`

        Returns:
            bool: True if successfull. False otherwise
        """
        # ? weird flex but okay.
        formatted_ip = ip_address.replace(".", "\\.")
        core_logger.info(f"Deleted peer with ip {ip_address}")
        return (ConnectionPeerModel.delete()
                .where(ConnectionPeerModel.shared_ips.regexp(
                    rf"(?:[, ]|^){formatted_ip}(?:[, ]|$)"
                ) & ConnectionPeerModel.user == self.__model)
                .execute()) == 1

class ClientFactory(BaseModel):
    model_config = ConfigDict(ignored_types=(multimethod, ))

    tg_id: int

    def get_or_create_client(self, name: str, **kwargs) -> Client:
        """Retrieves or creates a record of the user in the database.
        Use this method when you're unsure whether the user already exists in the database or not."""
        try:
            model: UserModel = UserModel.get(UserModel.telegram_id == self.tg_id)

            if model.name != name:
                model.name = name
                model.save()
                with core_logger.contextualize(model=model):
                    core_logger.info(f"User has changed his username, updating it in DB")
        except DoesNotExist:
            model: UserModel = UserModel.create(telegram_id=self.tg_id, name=name, **kwargs)
            with core_logger.contextualize(model=model):
                core_logger.info(f"New user was created.")

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
        try:
            model = UserModel.get(UserModel.ip_address == ip_address)
            return Client(model=model, userdata=User.model_validate(model))
        except DoesNotExist:
            return None

    @staticmethod
    def select_clients() -> list[Client]:
        return [Client(model=i, userdata=User.model_validate(i)) for i in UserModel.select()]

    @staticmethod
    def select_peers() -> list[ConnectionPeer]:
        return [ConnectionPeer.model_validate(i) for i in ConnectionPeerModel.select()]

    @staticmethod
    def get_peer(ip_address: str) -> Optional[ConnectionPeer]:
        try:
            model = ConnectionPeerModel.get(ConnectionPeerModel.shared_ips == ip_address)
            return ConnectionPeer.model_validate(model)
        except DoesNotExist:
            return None

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

    @staticmethod
    def get_latest_peer_id() -> int:
        try:
            return ConnectionPeerModel.select(ConnectionPeerModel.id).order_by(SQL("id").desc()).limit(1)[0].id
        except IndexError: #? assuming that there're no peers in DB
            return 0

    @staticmethod
    def get_ip_addresses() -> list[str]:
        return [i.shared_ips for i in ConnectionPeerModel.select(ConnectionPeerModel.shared_ips)]

    @staticmethod
    def delete_peer(peer: ConnectionPeer) -> bool:
        return ConnectionPeerModel.delete().where(ConnectionPeerModel.id == peer.id).execute() == 1
