from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = 'sqlite:///data/candle.db'

engine = create_engine(SQLALCHEMY_DATABASE_URL)

Base = declarative_base()

db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
