from core.db.models import UserModel, ConnectionPeerModel
from typing import Iterable
from pydantic import BaseModel


class Client(BaseModel):
    tg_id: int

    def get_client(self, *criteria) -> UserModel:
        return UserModel.get(UserModel.telegram_id == self.tg_id, *criteria)
    
    def create_client(self, **kwargs):
        return UserModel.create(telegram_id=self.tg_id, **kwargs)

    class Meta:
        arbitrary_types_allowed=True
