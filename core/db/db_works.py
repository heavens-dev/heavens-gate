from core.db.models import UserModel, ConnectionPeerModel
from pydantic import BaseModel


class Client(BaseModel):
    tg_id: int

    def is_registered(self) -> bool:
        return UserModel.select().where(UserModel.telegram_id == self.tg_id).count() == 1

    def delete_client(self) -> bool:
        return UserModel.delete().where(UserModel.telegram_id == self.tg_id).execute() == 1

    def get_client(self) -> UserModel:
        return UserModel.get(UserModel.telegram_id == self.tg_id)
    
    def create_client(self, name: str, **kwargs) -> UserModel:
        return UserModel.create(telegram_id=self.tg_id, name=name, **kwargs)
    
    def add_peer(self, private_key: str, preshared_key: str, shared_ips: str):
        client = self.get_client()
        return ConnectionPeerModel.create(
            user=client, 
            private_key=private_key, 
            preshared_key=preshared_key, 
            shared_ips=shared_ips
        )

    class Meta:
        arbitrary_types_allowed=True