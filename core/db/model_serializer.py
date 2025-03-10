from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.db.enums import ClientStatusChoices, PeerStatusChoices, ProtocolType
from core.db.models import PeersTableModel


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: Union[int, str]
    name: str
    registered_at: datetime
    status: ClientStatusChoices
    expire_time: Optional[datetime] = Field(default=None)


class BasePeer(BaseModel):
    """
    Base class for peer-related models that inherits from BaseModel.
    This class represents the fundamental structure for peer entities in the system,
    containing common attributes for peer identification and status tracking.
    Attributes:
        id (int): The unique identifier for the peer.
        user_id (int): The identifier of the user associated with this peer.
        peer_name (str): The name or identifier for the peer.
        peer_type (ProtocolType): The protocol type of the peer.
        peer_status (PeerStatusChoices): The current status of the peer.
        peer_timer (datetime, optional): Timestamp for peer-related timing operations.
            Defaults to None.
    Note:
        This class uses Pydantic's ConfigDict with from_attributes=True to enable
        ORM mode for database model integration.
        Also, the populate_by_name parameter is set to True to populate the model
        fields using the attribute names.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(alias="peer.id")
    user_id: Union[int, str] = Field(alias="peer.user_id")

    peer_name: str = Field(alias="peer.peer_name")
    peer_type: ProtocolType = Field(alias="peer.peer_type")
    peer_status: PeerStatusChoices = Field(alias="peer.peer_status")
    peer_timer: Optional[datetime] = Field(default=None, alias="peer.peer_timer")

    @model_validator(mode="before")
    @classmethod
    def test(cls, data):
        if not isinstance(data, (dict, PeersTableModel)):
            if hasattr(data, "peer"):
                data.user_id = data.peer.user_id
                data.peer_name = data.peer.peer_name
                data.peer_type = data.peer.peer_type
                data.peer_status = data.peer.peer_status
                data.peer_timer = data.peer.peer_timer
        return data

class WireguardPeer(BasePeer):
    """
    A data model representing a Wireguard peer configuration.
    This class extends BasePeer and includes both standard Wireguard fields and
    Amnezia-specific customizations for peer configuration.
    Attributes:
        public_key (str): The public key used for peer identification and encryption
        private_key (str): The private key used for encryption/decryption
        preshared_key (str): Pre-shared key for additional security
        shared_ips (str): IP addresses allocated to this peer
        is_amnezia (bool): Flag indicating if this peer uses Amnezia-specific features
        Jc (Optional[int]): Current jitter value for Amnezia protocol
        Jmin (Optional[int]): Minimum jitter value for Amnezia protocol
        Jmax (Optional[int]): Maximum jitter value for Amnezia protocol
    """

    # Wireguard fields
    public_key: str
    private_key: str
    preshared_key: str
    shared_ips: str

    # AmneziaWG-specific fields
    is_amnezia: bool
    Jc: Optional[int] = Field(default=None)
    Jmin: Optional[int] = Field(default=None)
    Jmax: Optional[int] = Field(default=None)

class XrayPeer(BasePeer):
    """A data model representing an XRay peer configuration.
    This class extends BasePeer and defines the structure for XRay peer data,
    including inbound connection identification and flow information.
    Attributes:
        inbound_id (int): The unique identifier for the inbound connection.
        flow (str): The flow configuration string for the XRay peer.
    """

    # Xray fields
    inbound_id: int
    flow: str
