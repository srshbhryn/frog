import functools
from datetime import datetime
from typing import Optional

from sqlalchemy import func

from frog.types import Pair, Price
from tadpoles.types import Exchange

from .db import db, Candle


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

    def _convert_to_whole_minute_timestamp(self, timestamp: datetime) -> int:
        return timestamp.replace(second=0, microsecond=0).timestamp()

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
            from_timestamp_whole_minute += 60

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
    ) -> dict[datetime, Price]:
        return {
            datetime.fromtimestamp(timestamp): Price(price)
            for timestamp, price in db.query(Candle.timestamp, Candle.open_price)
            .filter(
                *[
                    *self.pair_filter_args,
                    Candle.timestamp >= self._convert_to_whole_minute_timestamp(from_timestamp),
                    Candle.timestamp <= self._convert_to_whole_minute_timestamp(to_timestamp),
                ],
            )
            .order_by(Candle.timestamp)
            .all()
        }
