import decimal
import datetime

from tadpoles.timescaledb import Base, engine

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DECIMAL, String


class Candle(Base):
    __tablename__ = "candle"
    __table_args__ = {
        'timescaledb_hypertable': {
            'time_column_name': 'timestamp',
            'chunk_time_interval': '1 day',
        }
    }

    base_asset: Mapped[str] = mapped_column(String(8), primary_key=True)
    quote_asset: Mapped[str] = mapped_column(String(8), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(8), primary_key=True)
    resolution: Mapped[datetime.timedelta] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(primary_key=True)
    min_price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    max_price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    open_price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    close_price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    volume: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))


Base.metadata.create_all(engine)
