import datetime
import random
from typing import Optional

from multimethod import multimethod
from peewee import SQL, DoesNotExist
from pydantic import BaseModel, ConfigDict, PrivateAttr

from core.db.enums import ClientStatusChoices, PeerStatusChoices, ProtocolType
from core.db.model_serializer import BasePeer, User, WireguardPeer
from core.db.models import (PeersTableModel, UserModel, WireguardPeerModel,
                            XrayPeerModel, db)
from core.logs import core_logger
from core.wg.keygen import (generate_preshared_key, generate_private_key,
                            generate_public_key)

BASE_PEER_FIELDS = ("id",
                    "user_id",
                    "peer_name",
                    "peer_type",
                    "peer_status",
                    "peer_timer")

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
        """
        Updates client data in the database using provided keyword arguments.

        Args:
            **kwargs: Variable keyword arguments containing fields and values to update for the client.

        Returns:
            bool: True if exactly one record was updated, False otherwise.
        """
        return (self.__model.update(**kwargs)
                .where(UserModel.user_id == self.userdata.user_id)
                .execute()) == 1

    def __update_peer(self, peer_id: int, **kwargs) -> bool:
        """
        Updates information for a specific peer in the database.
        This method updates both base peer fields and protocol-specific fields for a given peer ID.

        Args:
            peer_id (int): The ID of the peer to update.
            **kwargs: Arbitrary keyword arguments containing the fields to update.
                     Can include both base peer fields and protocol-specific fields.
        Returns:
            bool: True if the update was successful. Returns False in cases of:
            - Peer not found
            - Unknown protocol type
            - Database errors during update
            - Transaction failures
        Raises:
            No exceptions are raised as they are caught and logged internally.
        Example:
            >>> Client(...).__update_peer(1, name="new_name", public_key="new_key")
            True
        """
        peer_fields = {}
        protocol_specific_fields = {}

        for k, v in kwargs.items():
            if k in BASE_PEER_FIELDS:
                peer_fields[k] = v
            else:
                protocol_specific_fields[k] = v

        with db.atomic() as transaction:
            try:
                if peer_fields:
                    is_updated = (
                        PeersTableModel.update(**peer_fields)
                        .where(PeersTableModel.id == peer_id)
                        .execute()
                    ) == 1
                    if not is_updated:
                        core_logger.error(f"Something went wrong while updating peer: {peer_id}")
                        return False
                if protocol_specific_fields:
                    protocol = PeersTableModel.get(PeersTableModel.id == peer_id).peer_type
                    match protocol:
                        case (ProtocolType.WIREGUARD,
                              ProtocolType.AMNEZIA_WIREGUARD):
                            return (WireguardPeerModel.update(**protocol_specific_fields)
                                .where(WireguardPeerModel.id == peer_id)
                                .execute()) == 1
                        case ProtocolType.XRAY:
                            return (XrayPeerModel.update(**protocol_specific_fields)
                                .where(XrayPeerModel.id == peer_id)
                                .execute()) == 1
                        case _:
                            core_logger.warning(f"Unknown protocol type: {protocol}")
                            return False
            except Exception as e:
                transaction.rollback()
                core_logger.error(f"Error while updating peer: {e}")
                return False

    def set_status(self, status: ClientStatusChoices) -> bool:
        self.userdata.status = status
        return self.__update_client(status=status.value)

    def set_expire_time(self, expire_time: datetime.datetime) -> bool:
        self.userdata.expire_time = expire_time
        return self.__update_client(expire_time=expire_time)

    def add_wireguard_peer(self,
                 shared_ips: str,
                 public_key: Optional[str] = None,
                 private_key: Optional[str] = None,
                 preshared_key: Optional[str] = None,
                 is_amnezia: Optional[bool] = False,
                 peer_name: str = None) -> WireguardPeer:
        """
        Adds wireguard peer to database. Automatically generates peer keys if they're not present in arguments.

        Returns `WireguardPeer`.
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
        return WireguardPeer.model_validate(WireguardPeerModel.create(
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

    def __get_peers(self, *criteria) -> list[BasePeer]:
        """Private method for working with peers"""
        return list(PeersTableModel.select()
                    .where(PeersTableModel.user_id == self.__model, *criteria))

    def get_peers(self) -> list[BasePeer]:
        """Get validated peers model(s)"""
        return [
            BasePeer.model_validate(model)
            for model in self.__get_peers()
        ]

    def change_peer_name(self, peer_id: int, peer_name: str):
        self.__update_peer(peer_id, peer_name=peer_name)

    def set_peer_status(self, peer_id: int, peer_status: PeerStatusChoices):
        self.__update_peer(peer_id, peer_status=peer_status.value)

    def set_peer_timer(self, peer_id, time: datetime.datetime):
        self.__update_peer(peer_id, peer_timer=time)

    # TODO: include Xray peers
    def get_connected_peers(self) -> list[WireguardPeer]:
        return [
            WireguardPeer.model_validate(model)
            for model in self.__get_peers(WireguardPeerModel.peer_status == PeerStatusChoices.STATUS_CONNECTED.value)
        ]

    # TODO: get rid of multimethod
    @multimethod
    def delete_peer(self) -> bool:
        """Delete peers by `telegram_id`

        Returns:
            bool: True if successfull. False otherwise
        """
        return (WireguardPeerModel.delete()
                .where(UserModel.user_id == self.userdata.user_id)
                .execute()) == 1

    # TODO: get rid of multimethod
    @multimethod
    def delete_peer(self, ip_address: str) -> bool:
        """Delete single peer by `ip_address`

        Returns:
            bool: True if successfull. False otherwise
        """
        # ? weird flex but okay.
        formatted_ip = ip_address.replace(".", "\\.")
        return (WireguardPeerModel.delete()
                .where(WireguardPeerModel.shared_ips.regexp(
                    rf"(?:[, ]|^){formatted_ip}(?:[, ]|$)"
                ) & WireguardPeerModel.user == self.__model)
                .execute()) == 1

class ClientFactory(BaseModel):
    model_config = ConfigDict(ignored_types=(multimethod, ))

    tg_id: int

    def get_or_create_client(self, name: str, **kwargs) -> Client:
        """Retrieves or creates a record of the user in the database.
        Use this method when you're unsure whether the user already exists in the database or not."""
        try:
            model: UserModel = UserModel.get(UserModel.user_id == self.tg_id)

            if model.name != name:
                model.name = name
                model.save()
                with core_logger.contextualize(model=model):
                    core_logger.debug(f"User has changed his username, updating it in DB")
        except DoesNotExist:
            model: UserModel = UserModel.create(telegram_id=self.tg_id, name=name, **kwargs)
            with core_logger.contextualize(model=model):
                core_logger.info(f"New user was created.")

        return Client(model=model, userdata=User.model_validate(model))

    # TODO: get rid of multimethod
    @multimethod
    def get_client(self) -> Optional[Client]:
        try:
            model = UserModel.get(UserModel.user_id == self.tg_id)
            return Client(model=model, userdata=User.model_validate(model))
        except DoesNotExist:
            return None

    # TODO: get rid of multimethod
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

    # ! Candidate for removal. Not used in any real code.
    @staticmethod
    def select_peers() -> list[WireguardPeer]:
        return [WireguardPeer.model_validate(i) for i in WireguardPeerModel.select()]

    @staticmethod
    def get_peer(ip_address: str) -> Optional[WireguardPeer]:
        try:
            model = WireguardPeerModel.get(WireguardPeerModel.shared_ips == ip_address)
            return WireguardPeer.model_validate(model)
        except DoesNotExist:
            return None

    # TODO: get rid of multimethod
    @multimethod
    @staticmethod
    def delete_client(ip_address: str) -> bool:
        return UserModel.delete().where(UserModel.ip_address.contains(ip_address)).execute() == 1

    # TODO: get rid of multimethod
    @multimethod
    def delete_client(self) -> bool:
        return UserModel.delete_by_id(self.tg_id)

    @staticmethod
    def count_clients() -> int:
        return UserModel.select().count()

    @staticmethod
    def get_latest_peer_id() -> int:
        try:
            return PeersTableModel.select(PeersTableModel.id).order_by(SQL("id").desc()).limit(1)[0].id
        except IndexError: #? assuming that there're no peers in DB
            return 0

    @staticmethod
    def get_used_ip_addresses() -> list[str]:
        return [i.shared_ips for i in WireguardPeerModel.select(WireguardPeerModel.shared_ips)]

    @staticmethod
    def delete_peer(peer: BasePeer) -> bool:
        return PeersTableModel.delete().where(PeersTableModel.id == peer.id).execute() == 1
