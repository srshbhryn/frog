import decimal
import datetime

import sqlalchemy
import sqlalchemy.orm

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DECIMAL, String, Index, Enum

from frog.types import Asset
from tadpoles.types import Exchange

from tadpoles.timescaledb import Base, get_engine



class SimZero(Base):
    __tablename__ = "sim_zero"
    __table_args__ = {
        'timescaledb_hypertable': {
            'time_column_name': 'timestamp',
            'chunk_time_interval': '1 day',
        }
    }

    # simulation params:
    base_asset: Mapped[Asset] = mapped_column(Enum(
        Asset,
        name='asset_enum',
        native_enum=True,
        create_type=True,
    ), primary_key=True)
    quote_asset: Mapped[Asset] = mapped_column(Enum(
        Asset,
        name='asset_enum',
        native_enum=True,
        create_type=True,
    ), primary_key=True)
    exchange_0: Mapped[Exchange] = mapped_column(Enum(
        Exchange,
        name='exchange_enum',
        native_enum=True,
        create_type=True,
    ), primary_key=True)
    exchange_1: Mapped[Exchange] = mapped_column(Enum(
        Exchange,
        name='exchange_enum',
        native_enum=True,
        create_type=True,
    ), primary_key=True)
    exchange_0_fee: Mapped[float]
    exchange_1_fee: Mapped[float]
    timestamp: Mapped[datetime.datetime] = mapped_column(primary_key=True)  # start of the simulation
    simulation_period: Mapped[datetime.timedelta] = mapped_column(primary_key=True)
    sell_buy_threshold: Mapped[float] = mapped_column(primary_key=True)
    buy_sell_threshold: Mapped[float] = mapped_column(primary_key=True)
    sell_buy_amount: Mapped[float] = mapped_column(primary_key=True)
    buy_sell_amount: Mapped[float] = mapped_column(primary_key=True)
    exchange_0_initial_base: Mapped[float]
    exchange_0_initial_quote: Mapped[float]
    exchange_1_initial_base: Mapped[float]
    exchange_1_initial_quote: Mapped[float]
    # prices quality:
    exchange_0_number_of_missing_points: Mapped[int]
    exchange_1_number_of_missing_points: Mapped[int]
    number_of_total_points: Mapped[int]
    # simulation results:
    exchange_0_final_base: Mapped[float]
    exchange_0_final_quote: Mapped[float]
    exchange_1_final_base: Mapped[float]
    exchange_1_final_quote: Mapped[float]
    exchange_0_initial_value_in_base: Mapped[float]
    exchange_0_initial_value_in_quote: Mapped[float]
    exchange_1_initial_value_in_base: Mapped[float]
    exchange_1_initial_value_in_quote: Mapped[float]
    exchange_0_initial_value_in_base: Mapped[float]
    exchange_0_initial_value_in_quote: Mapped[float]
    exchange_1_initial_value_in_base: Mapped[float]
    exchange_1_initial_value_in_quote: Mapped[float]
    exchange_0_final_value_in_base: Mapped[float]
    exchange_0_final_value_in_quote: Mapped[float]
    exchange_1_final_value_in_base: Mapped[float]
    exchange_1_final_value_in_quote: Mapped[float]
    trading_detail_buy_sell_trade_count: Mapped[int]
    trading_detail_sell_buy_trade_count: Mapped[int]
    trading_detail_buy_sell_cant_trade_count: Mapped[int]
    trading_detail_sell_buy_cant_trade_count: Mapped[int]


Base.metadata.create_all(get_engine())
