import peewee
from playhouse.sqlite_ext import SqliteExtDatabase


db = SqliteExtDatabase(None)

class BaseModel(peewee.Model):
    class Meta:
        database = db


class User(BaseModel):
    ...


def init_db(path: str):
    db.init(database=path)
    db.connect()
    db.create_tables()
    return db
