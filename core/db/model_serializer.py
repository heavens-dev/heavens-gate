from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from core.db.enums import ClientStatusChoices, PeerStatusChoices, ProtocolType


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
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
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int

    peer_name: str
    peer_type: ProtocolType
    peer_status: PeerStatusChoices
    peer_timer: Optional[datetime] = Field(default=None)

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
