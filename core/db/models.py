import datetime

from peewee import (BooleanField, CharField, DateTimeField, ForeignKeyField,
                    IntegerField, Model)
from playhouse.sqlite_ext import AutoIncrementField, SqliteExtDatabase

from core.db.enums import ClientStatusChoices, PeerStatusChoices, ProtocolType

db = SqliteExtDatabase(None, regexp_function=True)

class BaseModel(Model):
    class Meta:
        database = db


class UserModel(BaseModel):
    user_id = CharField(primary_key=True)
    name = CharField(default=None)
    status = IntegerField(
        default=ClientStatusChoices.STATUS_CREATED.value,
        choices=tuple(
            (status.value, status.name) for status in ClientStatusChoices
        )
    )
    expire_time = DateTimeField(default=None, null=True)
    registered_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "Users"


class PeersTableModel(BaseModel):
    id = AutoIncrementField()
    user = ForeignKeyField(UserModel, backref="peer", on_delete="CASCADE")
    """User ID field"""
    peer_name = CharField()
    peer_type = CharField(
        choices=tuple(
            (protocol.value, protocol.name) for protocol in ProtocolType
        )
    )
    peer_status = IntegerField(
        default=PeerStatusChoices.STATUS_DISCONNECTED.value,
        choices=tuple(
            (status.value, status.name) for status in PeerStatusChoices
        )
    )
    peer_timer = DateTimeField(default=None, null=True)
    class Meta:
        table_name = "PeersTable"


class WireguardPeerModel(BaseModel):
    peer = ForeignKeyField(PeersTableModel, backref="wireguard_peer", on_delete="CASCADE")
    """Peer ID field"""

    public_key = CharField()
    private_key = CharField()
    preshared_key = CharField()
    shared_ips = CharField()

    # AmneziaWG-specific fields
    is_amnezia = BooleanField(default=False)
    Jc = IntegerField(default=None, null=True)
    Jmin = IntegerField(default=None, null=True)
    Jmax = IntegerField(default=None, null=True)

    class Meta:
        table_name = "WireguardPeers"


class XrayPeerModel(BaseModel):
    peer = ForeignKeyField(PeersTableModel, backref="xray_peer", on_delete="CASCADE")
    """Peer ID field"""

    inbound_id = IntegerField()
    flow = CharField()

    class Meta:
        table_name = "XrayPeers"


def init_db(path: str):
    db.init(database=path, pragmas={"foreign_keys": 1})
    db.connect()
    db.create_tables((UserModel, PeersTableModel, WireguardPeerModel, XrayPeerModel))
    return db
