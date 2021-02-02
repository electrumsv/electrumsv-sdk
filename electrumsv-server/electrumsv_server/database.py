from typing import TYPE_CHECKING
import os

import peewee

from .constants import NAME_SQLITE, RequestState
from .exceptions import StartupError

if TYPE_CHECKING:
    from .application import ApplicationState


database_proxy = peewee.DatabaseProxy()


class BaseModel(peewee.Model):
    class Meta:
        database = database_proxy


class PaymentRequest(BaseModel):
    uid = peewee.BinaryUUIDField(primary_key=True)
    state = peewee.IntegerField(default=RequestState.UNKNOWN)
    description = peewee.TextField(null=True)
    date_expires = peewee.TimestampField(null=True, utc=True)
    date_created = peewee.TimestampField(utc=True)
    tx_hash = peewee.BlobField(null=True)


class PaymentRequestOutput(BaseModel):
    description = peewee.TextField(null=True)
    amount = peewee.IntegerField()
    script = peewee.BlobField()
    request = peewee.ForeignKeyField(PaymentRequest, backref="outputs")


class Payment(BaseModel):
    transaction = peewee.BlobField()
    refund_address = peewee.TextField(null=True)
    description = peewee.TextField(null=True)
    request = peewee.ForeignKeyField(PaymentRequest)


def open_sqlite_database(app: 'ApplicationState') -> peewee.Database:
    db_path = os.path.join(app.data_path, "electrumsv_server.sqlite")
    db = peewee.SqliteDatabase(db_path, pragmas = {
        'journal_mode': 'wal',
        'cache_size': -1024 * 64
    })
    return db


def open_database(app: 'ApplicationState') -> peewee.Database:
    if app.config.database == NAME_SQLITE:
        db = open_sqlite_database(app)
    else:
        raise StartupError(f"database: only {NAME_SQLITE} currently supported")

    database_proxy.initialize(db)
    db.connect()
    db.create_tables([
        PaymentRequest,
        PaymentRequestOutput,
        Payment,
    ], safe=True)
    db.close()
    return db

