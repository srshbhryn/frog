from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

TIMESCALEDB_URL = 'timescaledb://db:db@127.0.0.1:5477/db'

engine = create_engine(TIMESCALEDB_URL)

Base = declarative_base()

db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
