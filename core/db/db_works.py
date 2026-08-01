import datetime
import random
import secrets
from typing import Optional, Union

from peewee import DoesNotExist
from playhouse.shortcuts import model_to_dict
from pydantic import BaseModel, ConfigDict, PrivateAttr

from core.db.enums import (ClientStatusChoices, PeerStatusChoices,
                           ProtocolType, SubscriptionType)
from core.db.model_serializer import (BasePeer, Organization, User,
                                      WireguardPeer, XrayPeer)
from core.db.models import (OrganizationModel, OrganizationOwnerModel,
                            PeerModel, UserModel, WireguardPeerModel,
                            XrayPeerModel, db)
from core.logs import core_logger
from core.wg.keygen import (generate_preshared_key, generate_private_key,
                            generate_public_key)

# TODO: read BasePeer field names instead of hardcoding
BASE_PEER_FIELDS = ("id",
                    "user_id",
                    "name",
                    "type",
                    "status",
                    "active_until",
                    "last_connected_at")

class Client(BaseModel):
    """
    Client class for managing user data and associated peers in the database.
    This class provides an interface for handling CRUD operations related to users (and their
    associated connection peers) and high-level methods for peer management.

    Attributes:
        userdata (User): User information associated with this client.
        __model (UserModel): Private attribute referencing the user's database model.

    Notes:
        - The class uses a private model instance to interact with the database.
        - Peer operations are type-specific with protocol-dependent behavior.
    """
    model_config = ConfigDict()

    userdata: User
    __model: UserModel = PrivateAttr(init=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "model" not in kwargs.keys():
            raise AttributeError("model attribute was not found in kwargs.")
        self.__model = kwargs["model"]

    @core_logger.catch()
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

    @core_logger.catch()
    def __add_peer(self,
                   name: str,
                   peer_type: ProtocolType,
                   **kwargs
                   ) -> Optional[Union[WireguardPeer, XrayPeer]]:
        """
        Adds a new peer to the database, based on the provided peer type and keyword arguments.

        Args:
            name (str): The name of the peer to add.
            peer_type (ProtocolType): The type of the peer to add.
            **kwargs: Arbitrary keyword arguments containing the fields to add to the peer.

        Returns:
            Optional[BasePeer]: A validated peer model if the peer was added successfully,
                               or None if the peer was not added.
        """
        with db.atomic() as transaction:
            try:
                peer = BasePeer.model_validate(PeerModel.create(
                    user_id=self.__model,
                    type=peer_type.value,
                    name=name
                ))
                core_logger.debug(f"Created a new base peer with ID: {peer.peer_id}")
                match peer_type:
                    case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
                        wg_peer_model = WireguardPeerModel.create(
                            peer=peer.id,
                            **kwargs
                        )
                        # there's probably an easier way to extract all data
                        # but i'm lazy, so leaving it like that until idk
                        return WireguardPeer(
                            **peer.model_dump(exclude=("id",)),
                            **model_to_dict(
                                wg_peer_model,
                                exclude=[WireguardPeerModel.peer]
                            ),
                        )
                    case ProtocolType.XRAY:
                        xray_peer = XrayPeerModel.create(
                            peer=peer.id,
                            **kwargs
                        )
                        return XrayPeer(
                            **peer.model_dump(exclude=("id",)),
                            **model_to_dict(
                                xray_peer,
                                exclude=[XrayPeerModel.peer]
                            ),
                        )
                    case _:
                        core_logger.warning(f"Unknown protocol type: {peer_type}")
                        return None
            except Exception as e:
                transaction.rollback()
                core_logger.exception(f"Error while adding peer: {e}")
                return None

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
                        PeerModel.update(**peer_fields)
                        .where(PeerModel.id == peer_id)
                        .execute()
                    ) == 1
                    if not is_updated:
                        core_logger.error(f"Something went wrong while updating peer: {peer_id}")
                        return False
                if protocol_specific_fields:
                    protocol = PeerModel.get(PeerModel.id == peer_id).type
                    match protocol:
                        case ProtocolType.WIREGUARD | \
                             ProtocolType.AMNEZIA_WIREGUARD:
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

    def add_wireguard_peer(
            self,
            shared_ips: str,
            public_key: Optional[str] = None,
            private_key: Optional[str] = None,
            preshared_key: Optional[str] = None,
            is_amnezia: Optional[bool] = False,
            peer_name: Optional[str] = None
        ) -> Optional[WireguardPeer]:
        """
        Adds wireguard peer to database. Automatically generates peer keys if they're not present in arguments.

        Args:
            shared_ips (str): Comma-separated list of IPs.
            public_key (Optional[str]): Public key of the peer. Defaults to None.
            private_key (Optional[str]): Private key of the peer. Defaults to None.
            preshared_key (Optional[str]): Preshared key of the peer. Defaults to None.
            is_amnezia (Optional[bool]): True if the peer is an Amnezia peer. Defaults to False.
            peer_name (Optional[str]): Name of the peer. Defaults to None.

        Returns:
            `WireguardPeer`: Validated `WireguardPeer` model if the peer was added successfully.
        """
        wireguard_args = {
            "shared_ips": shared_ips
        }
        wireguard_args["private_key"] = private_key or generate_private_key(is_amnezia=is_amnezia)
        wireguard_args["public_key"] = public_key or generate_public_key(wireguard_args["private_key"], is_amnezia=is_amnezia)
        wireguard_args["preshared_key"] = preshared_key or generate_preshared_key(is_amnezia=is_amnezia)

        if not peer_name:
            peer_name = f"{self.userdata.name}_{ClientFactory.get_latest_peer_id() + 1}"

        Jc, Jmin, Jmax = None, None, None
        if is_amnezia:
            # ? recommended values for: -- [3, 10], Jmin = 50, Jmax = 1000
            # ? so they can be changed, but we'll see
            Jc = random.randint(3, 127)
            Jmin = random.randint(3, 700)
            Jmax = random.randint(Jmin + 1, 1270)

        wireguard_args["is_amnezia"] = is_amnezia
        wireguard_args["Jc"] = Jc
        wireguard_args["Jmin"] = Jmin
        wireguard_args["Jmax"] = Jmax

        return self.__add_peer(
            name=peer_name,
            peer_type=ProtocolType.AMNEZIA_WIREGUARD if is_amnezia else ProtocolType.WIREGUARD,
            **wireguard_args
        )

    def add_xray_peer(self, flow: str, inbound_id: int, peer_name: Optional[str] = None) -> XrayPeer:
        hash_id = secrets.token_urlsafe(8)

        if not peer_name:
            peer_name = f"{self.userdata.name}_{hash_id}"

        peer = self.__add_peer(
            name=peer_name,
            peer_type=ProtocolType.XRAY,
            flow=flow,
            inbound_id=inbound_id,
            hash_id=hash_id
        )
        with core_logger.contextualize(peer=peer):
            core_logger.info(f"New peer was created.")
        return peer

    def __get_peers(
            self,
            protocol_type: Optional[ProtocolType] = None,
            *criteria
        ) -> Optional[list[Union[PeerModel, WireguardPeerModel, XrayPeerModel]]]:
        """
        Retrieve peers from the database based on protocol type and additional criteria.

        This private method fetches peer information from the database. The query structure and
        returned model types depend on the specified protocol type.

        Args:
            protocol_type (Optional[ProtocolType]): The protocol type to filter peers by.
                If specified as WIREGUARD or AMNEZIA_WIREGUARD, returns WireguardPeerModel data.
                If specified as XRAY, returns XrayPeerModel data.
                If None or any other value, returns basic PeersTableModel data.
            *criteria: Additional criteria to filter the query results.

        Returns:
            Optional[list[Union[PeersTableModel, WireguardPeerModel, XrayPeerModel]]]:
                A list of peer models matching the specified criteria. The model type depends on
                the protocol_type parameter. Returns None if no peers are found.
        """
        match protocol_type:
            case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
                return list(
                    WireguardPeerModel.select(
                        PeerModel,
                        WireguardPeerModel,
                        PeerModel.id.alias("peer_id")
                    )
                    .join(
                        PeerModel,
                        on=(PeerModel.id == WireguardPeerModel.peer)
                    )
                    .where(PeerModel.user == self.__model, *criteria)
                )
            case ProtocolType.XRAY:
                return list(XrayPeerModel.select(
                                PeerModel,
                                XrayPeerModel,
                                PeerModel.id.alias("peer_id")
                            )
                            .join(
                                PeerModel,
                                on=(PeerModel.id == XrayPeerModel.peer)
                            )
                            .where(PeerModel.user == self.__model, *criteria)
                            )
            case _:
                return list(PeerModel.select()
                            .where(PeerModel.user == self.__model, *criteria)
                            )

    @core_logger.catch()
    def get_wireguard_peers(self, is_amnezia: bool) -> list[WireguardPeer]:
        # is_amnezia doesn't really matter here, but it's here for consistency
        peer_models = self.__get_peers(ProtocolType.WIREGUARD if not is_amnezia
                                       else ProtocolType.AMNEZIA_WIREGUARD)

        return [WireguardPeer.model_validate(model) for model in peer_models]

    def get_xray_peers(self) -> list[XrayPeer]:
        peer_models = self.__get_peers(ProtocolType.XRAY)
        return [XrayPeer.model_validate(model) for model in peer_models]

    def get_all_peers(
            self,
            protocol_specific: bool = False
        ) -> Union[list[BasePeer], list[Union[WireguardPeer, XrayPeer]]]:
        """
        Retrieve all peers from the database.
        This method fetches both Wireguard and Xray peers from the database. The peers can be
        returned either as base peer models or as protocol specific peer types.
        Args:
            protocol_specific (bool):
                If True, returns protocol specific Wireguard and Xray peer models.
                If False, returns base peer models. Defaults to False.
        Returns:
            Union[list[BasePeer], list[Union[WireguardPeer, XrayPeer]]]: A list of peers.
            When `protocol_specific` is False, returns a list of `BasePeer` objects.
            When `protocol_specific` is True, returns a concatenated list of `WireguardPeer` and `XrayPeer` objects.
        """
        if protocol_specific:
            return self.get_wireguard_peers(is_amnezia=True) # + self.get_xray_peers() TODO: remove or adapt after xray_worker is fixed

        return [
            BasePeer.model_validate(model)
            for model in self.__get_peers()
        ]

    @core_logger.catch()
    def change_peer_name(self, peer_id: int, peer_name: str) -> bool:
        result = self.__update_peer(peer_id, name=peer_name)
        with core_logger.contextualize(peer_id=peer_id, result=result):
            core_logger.info(f"Tried to change Peer name to {peer_name}")
        return result

    def set_status(self, status: ClientStatusChoices) -> bool:
        self.userdata.status = status
        return self.__update_client(status=status.value)

    def set_subscription_type(self, subscription_type: SubscriptionType) -> bool:
        self.userdata.subscription_type = subscription_type
        return self.__update_client(subscription_type=subscription_type.value)


    def set_subscription_expiry(self, expire_time: datetime.datetime) -> bool:
        self.userdata.subscription_expiry = expire_time
        core_logger.info(f"Setting subscription expiry to {expire_time} for user {self.userdata.user_id}")
        return self.__update_client(subscription_expiry=expire_time)

    def set_remnawave_user_uuid(self, uuid: str) -> bool:
        self.userdata.remnawave_user_uuid = uuid
        return self.__update_client(remnawave_user_uuid=uuid)

    def clear_subscription(self) -> bool:
        """Resets the user's subscription type and expiry date to None (unpaid)."""
        self.userdata.subscription_type = None
        self.userdata.subscription_expiry = None
        return self.__update_client(subscription_type=None, subscription_expiry=None)

    def set_organization_id(self, org_id: int) -> bool:
        self.userdata.organization_id = org_id
        return self.__update_client(organization_id=org_id)

    @core_logger.catch()
    def set_peer_status(self, peer_id: int, peer_status: PeerStatusChoices) -> bool:
        result = self.__update_peer(peer_id, status=peer_status.value)
        with core_logger.contextualize(peer_id=peer_id, result=result):
            core_logger.debug(f"Tried to change peer status to {peer_status}")
        return result

    @core_logger.catch()
    def set_peer_active_time(self, peer_id: int, time: datetime.datetime) -> bool:
        result = self.__update_peer(peer_id, active_until=time)
        with core_logger.contextualize(peer_id=peer_id, result=result):
            core_logger.debug(f"Tried to change peer active time to {time}")
        return result

    @core_logger.catch()
    def get_connected_peers(self) -> list[BasePeer]:
        return [
            BasePeer.model_validate(model)
            for model in self.__get_peers(None, PeerModel.status == PeerStatusChoices.STATUS_CONNECTED.value)
        ]

    def get_owned_org(self) -> Optional["OrganizationRepository"]:
        """
        Retrieves the organization owned by the user, if any.

        Returns:
            OrganizationRepository: The organization repository object if the user is an owner, None otherwise.
        """
        try:
            org_owner = OrganizationOwnerModel.get(OrganizationOwnerModel.user == self.__model)
            org = OrganizationModel.get(OrganizationModel.id == org_owner.organization_id)
            return OrganizationRepository(orgdata=Organization.model_validate(org), model=org)
        except DoesNotExist:
            return None

    def delete_peers(self) -> bool:
        """
        Deletes all peer records associated with the current user from the database.

        Returns:
            bool: True if operation was successfully executed, False otherwise.
        """
        return (PeerModel.delete()
                .where(PeerModel.user == self.userdata.user_id)
                .execute()) == 1

    def delete_wireguard_peer_by_ip(self, ip_address: str) -> bool:
        """Delete wireguard peer by `ip_address`

        Deletes the peer from PeersTableModel which will cascade to WireguardPeerModel.

        Returns:
            bool: True if successful. False otherwise
        """
        # format IP for regex pattern
        formatted_ip = ip_address.replace(".", "\\.")

        try:
            peer = (PeerModel
                   .select()
                   .join(WireguardPeerModel)
                   .where(WireguardPeerModel.shared_ips.regexp(
                       rf"(?:[, ]|^){formatted_ip}(?:[, ]|$)"
                   ) )
                   .where(PeerModel.user == self.__model)
                   .get())

            peer.delete_instance()
            return True
        except DoesNotExist:
            core_logger.info(f"Wireguard peer with IP {ip_address} not found.")
            return False

# TODO: split ClientFactory class into different files, depending on the type of object
class ClientFactory(BaseModel):
    model_config = ConfigDict()

    user_id: Union[int, str]

    def get_or_create_client(self, name: str, **kwargs) -> tuple[Client, bool]:
        """Retrieves or creates a record of the user in the database.
        Use this method when you're unsure whether the user already exists in the database or not.

        Returns:
            tuple[Client, bool]:
                A tuple containing the created or retrieved `Client` object
                and a boolean indicating whether it was created.
        """
        created: bool = False
        if not name:
            raise ValueError("Name cannot be empty.")

        try:
            model: UserModel = UserModel.get(UserModel.user_id == self.user_id)

            if model.name != name:
                model.name = name
                model.save()
                with core_logger.contextualize(model=model):
                    core_logger.info(f"User has changed his username, updating it in DB")
        except DoesNotExist:
            model: UserModel = UserModel.create(
                user_id=self.user_id,
                name=name,
                vless_sub_token=secrets.token_urlsafe(8),
                **kwargs
            )
            with core_logger.contextualize(model=model):
                core_logger.info(f"New user was created.")
            created = True

        return (Client(model=model, userdata=User.model_validate(model)), created)

    def get_client(self) -> Optional[Client]:
        """
        Retrieves a Client instance associated with the user ID.

        Returns:
            Optional[Client]: A Client instance containing the user model and validated user data,
                             or None if the user does not exist in the database.
        """
        try:
            model = UserModel.get(UserModel.user_id == self.user_id)
            return Client(model=model, userdata=User.model_validate(model))
        except DoesNotExist:
            return None

    @staticmethod
    def get_client_by_id(user_id: Union[int, str]) -> Optional[Client]:
        """
        Retrieve a client by their user ID.

        Args:
            user_id (Union[int, str]): The unique identifier of the user to find.

        Returns:
            Optional[Client]: A Client instance containing the user model and validated user data,
                             or None if the user does not exist in the database.
        """
        try:
            model = UserModel.get(UserModel.user_id == user_id)
            return Client(model=model, userdata=User.model_validate(model))
        except DoesNotExist:
            return None

    @staticmethod
    def select_clients() -> list[Client]:
        """
        Retrieves all clients from the database.

        Returns:
            list[Client]: A list of Client objects.
        """
        return [Client(model=i, userdata=User.model_validate(i)) for i in UserModel.select()]

    @staticmethod
    def get_peer_by_id(peer_id: int, protocol_specific: bool = False) -> Optional[BasePeer]:
        try:
            model: PeerModel = PeerModel.get(PeerModel.id == peer_id)
            if protocol_specific:
                match model.type:
                    case ProtocolType.WIREGUARD.value | ProtocolType.AMNEZIA_WIREGUARD.value:
                        return WireguardPeer.model_validate(WireguardPeerModel.get(WireguardPeerModel.peer == peer_id))
                    case ProtocolType.XRAY.value:
                        return XrayPeer.model_validate(XrayPeerModel.get(XrayPeerModel.peer == peer_id))
                    case _:
                        core_logger.warning(f"Unknown protocol type: {model.type}")
                        return None
            return BasePeer.model_validate(model)
        except DoesNotExist:
            return None
        except Exception as e:
            core_logger.exception(f"Error while getting peer: {e}")
            return None

    @staticmethod
    def get_peer_by_ip(ip_address: str) -> Optional[WireguardPeer]:
        """
        Retrieve a WireguardPeer by IP address from the database.

        Args:
            ip_address (str): The IP address to search for.

        Returns:
            Optional[WireguardPeer]: The WireguardPeer object if found, None otherwise.
                Returns None if the peer doesn't exist or if there's an error during retrieval.
        """
        try:
            model = WireguardPeerModel.get(WireguardPeerModel.shared_ips == ip_address)
            return WireguardPeer.model_validate(model)
        except DoesNotExist:
            return None
        except Exception as e:
            core_logger.exception(f"Error while getting peer: {e}")
            return None

    @staticmethod
    def get_wireguard_peer(ip_address: str) -> Optional[WireguardPeer]:
        try:
            model = WireguardPeerModel.get(WireguardPeerModel.shared_ips == ip_address)
            return WireguardPeer.model_validate(model)
        except DoesNotExist:
            return None

    @staticmethod
    def get_xray_peer(peer_id: str) -> Optional[XrayPeer]:
        try:
            model = XrayPeerModel.get(XrayPeerModel.peer == peer_id)
            return XrayPeer.model_validate(model)
        except DoesNotExist:
            return None

    def delete_client(self) -> bool:
        return UserModel.delete_by_id(self.user_id)

    @staticmethod
    def delete_client_by_id(user_id: Union[int, str]) -> bool:
        return UserModel.delete_by_id(user_id)

    @staticmethod
    def count_clients() -> int:
        """Returns the number of clients in the database."""
        return UserModel.select().count()

    @staticmethod
    def get_latest_peer_id() -> int:
        """Returns the latest peer ID in the database.

        Returns:
            int: The latest peer ID if peers exist, or 0 if there are no peers in the database.
        """
        try:
            result = db.execute_sql(f"SELECT seq FROM sqlite_sequence WHERE name = 'Peers'")
            return result.fetchone()[0]
        except (IndexError, TypeError): # ? assuming that there're no peers in DB
            return 0

    @staticmethod
    def get_used_ip_addresses() -> list[str]:
        return [i.shared_ips for i in WireguardPeerModel.select(WireguardPeerModel.shared_ips)]

    @staticmethod
    def delete_peer(peer: BasePeer) -> Union[BasePeer, bool]:
        try:
            p = PeerModel.get(PeerModel.id == peer.peer_id)
            p.delete_instance()
            return p
        except DoesNotExist:
            core_logger.info(f"Peer with ID {peer.peer_id} not found.")
            return False

    @staticmethod
    def delete_peer_by_id(
        peer_id: int,
        protocol_specific: bool = False
    ) -> Union[BasePeer, WireguardPeer, XrayPeer, bool]:
        """
        Deletes a peer by their ID.
        Args:
            peer_id (int): The unique identifier of the peer to be deleted.
            protocol_specific (bool): If True, the method will return a protocol specific peer object.
                               If False, it will return a `BasePeer` object.
        Returns:
            Union[BasePeer, WireguardPeer, XrayPeer, bool]:
                Returns the deleted peer object if successful, `protocol_specific` if requested.
                Returns `False` if the peer was not found or if an error occurred during deletion.
        """
        try:
            peer: PeerModel = PeerModel.get(PeerModel.id == peer_id)

            if protocol_specific:
                match peer.type:
                    case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
                        serialized_model = WireguardPeer.model_validate(
                            WireguardPeerModel.get(WireguardPeerModel.peer == peer_id)
                        )
                    case ProtocolType.XRAY:
                        serialized_model = XrayPeer.model_validate(
                            XrayPeerModel.get(XrayPeerModel.peer == peer_id)
                        )
                    case _:
                        core_logger.warning(f"Unknown protocol type: {peer.type}")
                        serialized_model = BasePeer.model_validate(peer)
            else:
                serialized_model = BasePeer.model_validate(peer)

            # actually deleting the row from every table because of cascading
            peer.delete_instance()
            return serialized_model
        except DoesNotExist:
            core_logger.info(f"Peer with ID {peer_id} not found.")
            return False

class OrganizationRepository(BaseModel):
    model_config = ConfigDict()

    orgdata: Organization
    __model: OrganizationModel = PrivateAttr(init=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "model" not in kwargs.keys():
            raise AttributeError("model attribute was not found in kwargs.")
        self.__model = kwargs["model"]

    def __update_organization(self, **kwargs) -> bool:
        """
        Updates organization data in the database using provided keyword arguments.

        Args:
            **kwargs: Variable keyword arguments containing fields and values to update for the organization.

        Returns:
            bool: True if exactly one record was updated, False otherwise.
        """
        return (self.__model.update(**kwargs)
                .where(OrganizationModel.id == self.orgdata.org_id)
                .execute()) == 1

    def add_owner(self, user_id: Union[int, str]) -> bool:
        try:
            user = UserModel.get(UserModel.user_id == user_id)

            # ? user can be an owner of only one organization
            # ? if a query returns a record, it means that the user is already an owner of an organization
            is_already_owner = OrganizationOwnerModel.get_or_none(
                OrganizationOwnerModel.user == user
            )

            if is_already_owner:
                return False

            OrganizationOwnerModel.create(
                organization=self.__model,
                user=user
            )
            core_logger.info(f"User {user_id} was added as an owner of organization {self.orgdata.org_id}")

            return True
        except DoesNotExist:
            return False

    def remove_owner(self, user_id: Union[int, str]) -> bool:
        try:
            user = UserModel.get(UserModel.user_id == user_id)

            owner_record = OrganizationOwnerModel.get_or_none(
                OrganizationOwnerModel.organization == self.__model,
                OrganizationOwnerModel.user == user
            )

            if not owner_record:
                return False

            owner_record.delete_instance()
            core_logger.info(f"User {user_id} was removed as an owner of organization {self.orgdata.org_id}")

            return True
        except DoesNotExist:
            return False

    def get_owners(self, as_client: bool = False) -> list[Union[User, Client]]:
        """
        Retrieves all owners of the current organization.

        Args:
            as_client (bool): If True, returns a list of `Client` objects. If False, returns a list of `User` objects. Defaults to False.
        """
        owners = (UserModel
                  .select()
                  .join(OrganizationOwnerModel)
                  .where(OrganizationOwnerModel.organization == self.__model))
        if as_client:
            return [Client(model=owner, userdata=User.model_validate(owner)) for owner in owners]
        return [User.model_validate(owner) for owner in owners]

    def is_user_owner(self, user_id: Union[int, str]) -> bool:
        """Checks if a user is an owner of the current organization.

        Args:
            user_id (Union[int, str]): The unique identifier of the user to check.

        Returns:
            bool: True if the user is an owner of the organization, False otherwise.
        """
        try:
            user = UserModel.get(UserModel.user_id == user_id)

            owner_record = OrganizationOwnerModel.get_or_none(
                OrganizationOwnerModel.organization == self.__model,
                OrganizationOwnerModel.user == user
            )

            return owner_record is not None
        except DoesNotExist:
            return False

    def add_member(self, user_id: Union[int, str]) -> bool:
        try:
            user = UserModel.get(UserModel.user_id == user_id)
            if user.organization_id is not None:
                core_logger.info(
                    f"User {user_id} is already a member of organization {user.organization_id}. Cannot add to organization {self.orgdata.org_id}."
                )
                return False
            user.organization_id = self.orgdata.org_id
            user.save()
            core_logger.info(f"User {user_id} was added as a member of organization {self.orgdata.org_id}")
            return True
        except DoesNotExist:
            return False
        except Exception as e:
            core_logger.error(f"Error while adding organization member: {e}")
            return False

    def remove_member(self, user_id: Union[int, str]) -> bool:
        try:
            user = UserModel.get(UserModel.user_id == user_id)
            # ? organization_id is a foreign key that references the OrganizationModel.
            # organization_id_id is the raw FK value (id or None), so we don't
            # need to load the related object (and avoid None.id crashes).
            if user.organization_id_id != self.orgdata.org_id:
                core_logger.info(
                    f"User {user_id} is not a member of organization {self.orgdata.org_id}. Cannot remove."
                )
                return False
            user.organization_id = None
            user.save()
            core_logger.info(f"User {user_id} was removed as a member of organization {self.orgdata.org_id}")
            return True
        except DoesNotExist:
            return False
        except Exception as e:
            core_logger.error(f"Error while removing organization member: {e}")
            return False

    def get_members(self, as_client: bool = False) -> list[Union[User, Client]]:
        """
        Retrieves all members of the current organization.

        Args:
            as_client (bool): If True, returns a list of `Client` objects. If False, returns a list of `User` objects. Defaults to False.
        """
        members = UserModel.select().where(UserModel.organization_id == self.orgdata.org_id)
        if as_client:
            return [Client(model=member, userdata=User.model_validate(member)) for member in members]
        return [User.model_validate(member) for member in members]

    def is_user_member(self, user_id: Union[int, str]) -> bool:
        """Checks if a user is a member of the current organization.

        Args:
            user_id (Union[int, str]): The unique identifier of the user to check.

        Returns:
            bool: True if the user is a member of the organization, False otherwise.
        """
        try:
            user = UserModel.get(UserModel.user_id == user_id)
            return user.organization_id == self.orgdata.org_id
        except DoesNotExist:
            return False

    def set_organization_expiry(self, expire_time: datetime.datetime) -> bool:
        self.orgdata.subscription_expiry = expire_time
        core_logger.info(f"Setting subscription expiry to {expire_time} for organization {self.orgdata.org_id}")
        return self.__update_organization(subscription_expiry=expire_time)

    def set_organization_name(self, name: str) -> bool:
        self.orgdata.name = name
        core_logger.info(f"Setting organization name to {name} for organization {self.orgdata.org_id}")
        return self.__update_organization(name=name)

    # ? is this a buisness logic? idk, but for now it's here
    def sync_subscription_to_members(self) -> bool:
        """
        Synchronizes the subscription expiry date of the organization to all its members.

        Returns:
            bool: True if the synchronization was successful, False otherwise.
        """
        try:
            members = UserModel.select().where(UserModel.organization_id == self.orgdata.org_id)
            for member in members:
                member.subscription_expiry = self.orgdata.subscription_expiry
                member.subscription_type = SubscriptionType.ENTERPRISE.value
                member.save()
            core_logger.info(f"Synchronized subscription to all members of organization {self.orgdata.org_id}")
            return True
        except Exception as e:
            core_logger.error(f"Error while synchronizing subscription: {e}")
            return False

class OrganizationFactory(BaseModel):
    model_config = ConfigDict()

    @staticmethod
    def create_organization(name: str) -> OrganizationRepository:
        model = OrganizationModel.create(name=name)
        return OrganizationRepository(model=model, orgdata=Organization.model_validate(model))

    @staticmethod
    def get_by_id(org_id: int) -> Optional[OrganizationRepository]:
        try:
            model = OrganizationModel.get(OrganizationModel.id == org_id)
            return OrganizationRepository(model=model, orgdata=Organization.model_validate(model))
        except DoesNotExist:
            return None

    @staticmethod
    def get_by_name(name: str) -> Optional[OrganizationRepository]:
        try:
            model = OrganizationModel.get(OrganizationModel.name == name)
            return OrganizationRepository(model=model, orgdata=Organization.model_validate(model))
        except DoesNotExist:
            return None

    @staticmethod
    def select_organizations() -> list[OrganizationRepository]:
        return [OrganizationRepository(model=org, orgdata=Organization.model_validate(org)) for org in OrganizationModel.select()]

    @staticmethod
    def delete_organization(org_id: int) -> bool:
        try:
            org = OrganizationModel.get(OrganizationModel.id == org_id)
            org.delete_instance()
            return True
        except DoesNotExist:
            core_logger.info(f"Organization with ID {org_id} not found.")
            return False
