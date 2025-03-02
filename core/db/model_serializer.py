from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from core.db.enums import ClientStatusChoices, PeerStatusChoices


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    name: str
    ip_address: Optional[str] = None
    active_time: Optional[datetime] = None
    status: ClientStatusChoices
    expire_time: Optional[datetime] = None
    registered_at: datetime

class ConnectionPeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    public_key: str
    private_key: str
    preshared_key: str
    shared_ips: str
    peer_name: Optional[str] = None
    peer_status: PeerStatusChoices
    peer_timer: Optional[datetime] = None
    is_amnezia: bool
    Jc: Optional[int] = None
    Jmin: Optional[int] = None
    Jmax: Optional[int] = None
