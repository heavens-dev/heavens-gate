import datetime
import secrets

from peewee import (BooleanField, CharField, DateTimeField, ForeignKeyField,
                    IntegerField, Model)
from playhouse.sqlite_ext import AutoIncrementField, SqliteExtDatabase

from core.db.enums import (ClientStatusChoices, PeerStatusChoices,
                           ProtocolType, SubscriptionType)
from core.logs import core_logger

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
    registered_at = DateTimeField(default=datetime.datetime.now)
    subscription_type = CharField(default=None, null=True, choices=tuple(
        (subscription.value, subscription.name) for subscription in SubscriptionType)
    )
    """Type of subscription, e.g. "Default", "Premium", "ProMaxPlus", etc. Can be null for users without active subscription."""
    subscription_expiry = DateTimeField(default=None, null=True)

    vless_sub_token = CharField(default=None, null=True)
    """VLESS subscription token."""

    class Meta:
        table_name = "Users"


class PeerModel(BaseModel):
    id = AutoIncrementField()
    user = ForeignKeyField(UserModel, backref="peers", on_delete="CASCADE")
    """User ID field"""
    name = CharField()
    type = CharField(
        choices=tuple(
            (protocol.value, protocol.name) for protocol in ProtocolType
        )
    )
    status = IntegerField(
        default=PeerStatusChoices.STATUS_DISCONNECTED.value,
        choices=tuple(
            (status.value, status.name) for status in PeerStatusChoices
        )
    )
    active_until = DateTimeField(default=None, null=True)
    last_connected_at = DateTimeField(default=None, null=True)

    class Meta:
        table_name = "Peers"


class WireguardPeerModel(BaseModel):
    peer = ForeignKeyField(PeerModel, backref="wireguard_peer", on_delete="CASCADE", unique=True)
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
    peer = ForeignKeyField(PeerModel, backref="xray_config", on_delete="CASCADE", unique=True)
    """Peer ID field"""

    hash_id = CharField(unique=True, default=secrets.token_urlsafe(8))
    """Unique hash ID for the peer, used for identification in Xray. Generated as a URL-safe token."""

    inbound_id = IntegerField()
    flow = CharField()
    class Meta:
        table_name = "XrayPeers"


def init_db(path: str):
    db.init(database=path, pragmas={"foreign_keys": 1})
    db.connect()
    db.create_tables((UserModel, PeerModel, WireguardPeerModel, XrayPeerModel))
    core_logger.info(f"Database initialized at {path}")
    return db
