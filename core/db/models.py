from peewee import Model, CharField, DateTimeField, ForeignKeyField, IntegerField
from playhouse.sqlite_ext import SqliteExtDatabase
import datetime

from core.db.enums import StatusChoices

from core.wg.keygen import private_key, preshared_key, public_key


db = SqliteExtDatabase(None, regexp_function=True)

class BaseModel(Model):
    class Meta:
        database = db


class UserModel(BaseModel):
    telegram_id = CharField(primary_key=True)
    name = CharField(default=None)
    ip_address = CharField(default=None, null=True)
    active_time = DateTimeField(default=None, null=True)
    status = IntegerField(
        default=StatusChoices.STATUS_CREATED.value,
        choices=tuple(
            (status.value, status.name) for status in StatusChoices
        )
    )
    expire_time = DateTimeField(default=None, null=True)
    registered_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "Users"

class ConnectionPeerModel(BaseModel):
    user = ForeignKeyField(UserModel, backref="peer", on_delete="CASCADE")
    public_key = CharField()
    private_key = CharField()
    preshared_key = CharField()
    shared_ips = CharField()
    peer_name = CharField(default=None, null=True)

    def setup_peer_keys(self):
        peer_private_key = private_key()
        self.privatekey = peer_private_key
        self.public_key = public_key(peer_private_key)
        self.preshared_key = preshared_key()

    def peer_for_wg_server_config(self):
        return f"""
#{self.peer_name}
[Peer]
PublicKey = {self.public_key}
PresharedKey = {self.preshared_key}
AllowedIPs = {self.shared_ips}/32

"""

    class Meta:
        table_name = "ConnectionPeers"


def init_db(path: str):
    db.init(database=path, pragmas={"foreign_keys": 1})
    db.connect()
    db.create_tables((UserModel, ConnectionPeerModel))
    return db
