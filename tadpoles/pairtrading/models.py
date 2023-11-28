import datetime
import decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DECIMAL, String, ForeignKey


from tadpoles.timescaledb import Base, engine


class AlgorithmEntity(Base):
    __tablename__ = 'algorithm'

    id: Mapped[int] = mapped_column(primary_key=True)
    min_trading_beta: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    pricing_factor: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    wait_period: Mapped[datetime.timedelta]
    trading_threshold: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    regression_len: Mapped[int]
    regression_delta: Mapped[datetime.timedelta]
    long_asset: Mapped[str] = mapped_column(String(8))
    short_asset: Mapped[str] = mapped_column(String(8))
    quote_asset: Mapped[str] = mapped_column(String(8))
    results: Mapped[list['ResultEntity']] = relationship(
        back_populates='algorithm',
        cascade='all, delete-orphan',
    )


class ResultEntity(Base):
    __tablename__ = 'result'

    algorithm_id: Mapped[int] = mapped_column(ForeignKey("algorithm.id"), primary_key=True)
    algorithm: Mapped[AlgorithmEntity] = relationship(back_populates="results")

    timestamp: Mapped[datetime.datetime] = mapped_column(primary_key=True)
    regression_alpha: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    regression_beta: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    regression_long_price_normalizer: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    regression_short_price_normalizer: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    regression_number_of_long_prices: Mapped[int]
    regression_number_of_short_prices: Mapped[int]
    regression_number_of_timestamps_intersection_set: Mapped[int]
    did_short_trade_fill: Mapped[bool]
    did_long_trade_fill: Mapped[bool]
    added_long_asset_amount: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    added_short_asset_amount: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    added_quote_asset_amount: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))


Base.metadata.create_all(engine)
