from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from core.db.enums import StatusChoices


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    name: str
    ip_address: Optional[str]
    active_time: Optional[datetime]
    status: StatusChoices
    expire_time: Optional[datetime]
    registered_at: datetime

class ConnectionPeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    public_key: str
    private_key: str
    preshared_key: str
    shared_ips: str
    peer_name: Optional[str]
    def peer_for_wg_server_config(self):
        return f"""
#{self.peer_name}
[Peer]
PublicKey = {self.public_key}
PresharedKey = {self.preshared_key}
AllowedIPs = {self.shared_ips}/32

"""
