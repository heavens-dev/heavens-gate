from peewee import Model, CharField, DateTimeField, ForeignKeyField, IntegerField
from playhouse.sqlite_ext import SqliteExtDatabase
import datetime

from core.db.enums import StatusChoices


db = SqliteExtDatabase(None)

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

class ConnectionPeerModel(BaseModel):
    user = ForeignKeyField(UserModel, backref="peer")
    public_key = CharField()
    preshared_key = CharField()
    shared_ips = CharField()


def init_db(path: str):
    db.init(database=path)
    db.connect()
    db.create_tables((UserModel, ConnectionPeerModel))
    return db
