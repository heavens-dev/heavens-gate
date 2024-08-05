from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from core.db.enums import StatusChoices


class User(BaseModel):
    telegram_id: int
    name: str
    ip_address: Optional[str]
    active_time: Optional[datetime]
    status: StatusChoices
    expire_time: Optional[datetime]
    registered_at: datetime

    class Meta:
        orm_mode = True

class ConnectionPeer(BaseModel):
    id: int
    user_id: int
    public_key: str
    preshared_key: str
    shared_ips: str

    class Meta:
        orm_mode = True
