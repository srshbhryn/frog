from datetime import datetime
from typing import Optional

import sqlalchemy.exc

from frog.types import Pair, Price
from tadpoles.types import Exchange

from .db import db, Candle


class Oracle:
    def __init__(self, exchange: Exchange) -> None:
        self.exchange = exchange
        self.db = db

    def get_price(self, pair: Pair, timestamp: datetime) -> Optional[Price]:
        last_minutes_timestamp = timestamp.replace(second=0, microsecond=0).timestamp()
        try:
            candle = (
                db.query(Candle)
                .filter_by(
                    timestamp=last_minutes_timestamp,
                    base_asset=pair.base.value.lower(),
                    quote_asset=pair.quote.value.lower(),
                )
                .one()
            )
        except sqlalchemy.exc.NoResultFound:
            return None
        return Price(candle.close_price)
