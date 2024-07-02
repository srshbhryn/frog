import decimal
import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DECIMAL, String, Index

from frog.types import Asset
from tadpoles.timescaledb import Base, engine


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


class BinanceCandleFile(Base):
    __tablename__ = 'binance_candle_file'
    date: Mapped[datetime.date] = mapped_column(primary_key=True)
    resolution: Mapped[datetime.timedelta] = mapped_column(primary_key=True)
    base_asset: Mapped[Asset] = mapped_column(primary_key=True)
    quote_asset: Mapped[Asset] = mapped_column(primary_key=True)


class BinanceCandle(Base):
    __tablename__ = 'binance_candle'
    __table_args__ = {
        'timescaledb_hypertable': {
            'time_column_name': 'open_time',
            'chunk_time_interval': '1 day',
        }
    }

    base_asset: Mapped[Asset] = mapped_column(primary_key=True)
    quote_asset: Mapped[Asset] = mapped_column(primary_key=True)
    open_time: Mapped[datetime.datetime] = mapped_column(primary_key=True)
    resolution: Mapped[datetime.timedelta] = mapped_column(primary_key=True)
    min_price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    max_price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    open_price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    close_price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    volume: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    quote_value: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    trade_count: Mapped[int] = mapped_column()
    take_buy_base_volume: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    take_buy_quote_volume: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))


class Trade(Base):
    __tablename__ = "trade"
    __table_args__ = (
        Index(
            'exchange_pair_side_index',
            'exchange',
            'base_asset',
            'quote_asset',
            'is_buyer_maker',
        ),
        {
            'timescaledb_hypertable': {
                'time_column_name': 'timestamp',
                'chunk_time_interval': '1 day',
            }
        },
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    base_asset: Mapped[str] = mapped_column(String(8))
    quote_asset: Mapped[str] = mapped_column(String(8))
    exchange: Mapped[str] = mapped_column(String(8))
    timestamp: Mapped[datetime.datetime] = mapped_column(primary_key=True)
    is_buyer_maker: Mapped[bool]
    price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    amount: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))


Base.metadata.create_all(engine)
