from sqlalchemy import Column
from sqlalchemy.types import DECIMAL, String, INT

from .connection import Base, engine


class Candle(Base):
    __tablename__ = "candle"

    base_asset = Column(String(8), primary_key=True)
    quote_asset = Column(String(8), primary_key=True)
    exchange = Column(String(8), primary_key=True)
    resolution = Column(INT, primary_key=True)
    timestamp = Column(INT, primary_key=True)
    min_price = Column(DECIMAL(32, 16))
    max_price = Column(DECIMAL(32, 16))
    open_price = Column(DECIMAL(32, 16))
    close_price = Column(DECIMAL(32, 16))
    volume = Column(DECIMAL(32, 16))


Base.metadata.create_all(engine)
