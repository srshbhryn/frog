import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

TIMESCALEDB_URL = 'timescaledb://db:db@127.0.0.1:5477/db'

Base = declarative_base()

_engine = None

_db = None


def delete_db_and_engine():
    global _engine
    _engine = None
    global _db
    _db = None


def get_engine() -> sqlalchemy.Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(TIMESCALEDB_URL)
    return _engine


def get_db():
    global _db
    if _db is None:
        _db = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())()
    return _db
