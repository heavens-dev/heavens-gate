from peewee import Model, BigIntegerField, CharField, DateTimeField
from playhouse.sqlite_ext import SqliteExtDatabase


db = SqliteExtDatabase(None)

class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    id = BigIntegerField(primary_key=True)
    name = CharField(default=None)
    telegram_id = CharField()
    ip_address = CharField()
    active_time = DateTimeField()
    status = CharField()
    expire_time = DateTimeField()

class ConnectionPeers(BaseModel):
    id = BigIntegerField(foreign_key=User.id)
    private_key = CharField()
    preshared_key = CharField()
    shared_ips = CharField()


def init_db(path: str):
    db.init(database=path)
    db.connect()
    db.create_tables()
    return db
