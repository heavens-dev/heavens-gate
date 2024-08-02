from peewee import Model, BigIntegerField, CharField, DateTimeField, ForeignKeyField
from playhouse.sqlite_ext import SqliteExtDatabase, AutoIncrementField
import datetime


db = SqliteExtDatabase(None)

class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    id = AutoIncrementField(primary_key=True)
    name = CharField(default=None)
    telegram_id = CharField(unique=True)
    ip_address = CharField()
    active_time = DateTimeField()
    status = CharField()
    expire_time = DateTimeField()
    registered_at = DateTimeField(default=datetime.datetime.now)

class ConnectionPeers(BaseModel):
    id = ForeignKeyField(User, to_field="id", backref="peers")
    private_key = CharField()
    preshared_key = CharField()
    shared_ips = CharField()


def init_db(path: str):
    db.init(database=path)
    db.connect()
    db.create_tables()
    return db
