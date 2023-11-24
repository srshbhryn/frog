import decimal


from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DECIMAL, String, ForeignKey

from .connection import Base, engine


class AlgorithmEntity(Base):
    __tablename__ = 'algorithm'

    id: Mapped[int] = mapped_column(primary_key=True)
    min_trading_beta: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    pricing_factor: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    wait_period: Mapped[int]
    trading_threshold: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    regression_len: Mapped[int]
    regression_delta: Mapped[int]  # in seconds
    long_asset: Mapped[str] = mapped_column(String(8))
    short_asset: Mapped[str] = mapped_column(String(8))
    quote_asset: Mapped[str] = mapped_column(String(8))


class ResultEntity(Base):
    __tablename__ = 'result'

    algorithm_id: Mapped[int] = mapped_column(ForeignKey("algorithm.id"), primary_key=True)
    algorithm: Mapped[AlgorithmEntity] = relationship(back_populates="results")

    timestamp: Mapped[int] = mapped_column(primary_key=True)
    regression_alpha: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    regression_beta: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    regression_long_price_normalizer: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    regression_short_price_normalizer: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))
    did_short_trade_fill: Mapped[bool]
    did_long_trade_fill: Mapped[bool]
    gain: Mapped[decimal.Decimal] = mapped_column(DECIMAL(32, 16))


Base.metadata.create_all(engine)
