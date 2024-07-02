from decimal import Decimal
import functools
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
import numpy as np

from frog.types import Pair, Price
from tadpoles.types import Exchange
from tadpoles.timescaledb import get_db

from .models import Candle


db = get_db()

class Oracle:
    def __init__(self, exchange: Exchange, pair: Pair) -> None:
        self.exchange = exchange
        self.pair = pair

    @functools.cached_property
    def pair_filter_args(self) -> list:
        return [
            Candle.base_asset == self.pair.base.value,
            Candle.quote_asset == self.pair.quote.value,
        ]

    def _convert_to_whole_minute_timestamp(self, timestamp: datetime) -> datetime:
        return timestamp.replace(second=0, microsecond=0)

    def get_price(self, timestamp: datetime) -> Optional[Price]:
        candle = (
            db.query(Candle)
            .filter(
                *[
                    *self.pair_filter_args,
                    Candle.timestamp == self._convert_to_whole_minute_timestamp(timestamp),
                ],
            )
            .first()
        )

        if candle is None:
            return None
        return Price(candle.close_price)

    def get_timerange_min_and_max_prices(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
    ) -> tuple[Optional[Price], Optional[Price]]:
        from_timestamp_whole_minute = self._convert_to_whole_minute_timestamp(from_timestamp)
        if from_timestamp_whole_minute != from_timestamp.timestamp():
            from_timestamp_whole_minute += timedelta(minutes=1)

        min_price, max_price = (
            db.query(
                func.min(Candle.min_price),
                func.max(Candle.max_price),
            )
            .filter(
                *[
                    *self.pair_filter_args,
                    Candle.timestamp >= from_timestamp_whole_minute,
                    Candle.timestamp <= self._convert_to_whole_minute_timestamp(to_timestamp),
                ],
            )
            .first()
        )
        if min_price is None or max_price is None:
            return None, None

        return Price(min_price), Price(max_price)

    def get_timerange_prices(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
    ) -> list[float]:
        return [
            float(price)
            for price, *_ in db.query(Candle.open_price)
            .filter(
                *[
                    *self.pair_filter_args,
                    Candle.timestamp >= self._convert_to_whole_minute_timestamp(from_timestamp),
                    Candle.timestamp <= self._convert_to_whole_minute_timestamp(to_timestamp),
                ],
            )
            .order_by(Candle.timestamp)
            .all()
        ]

    def get_timerange_returns(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
    ) -> np.array:
        prices = self.get_timerange_prices(
            from_timestamp - timedelta(minutes=1),
            to_timestamp,
        )
        return np.array([(p - q) / q for p, q in zip(prices[:-1], prices[1:])])
