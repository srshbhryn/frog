import datetime
import logging

from frog.types import Asset

from tadpoles.timescaledb import get_db
from tadpoles.types import Exchange
from tadpoles.prices.models import Candle


def _fix_missing_prices(
    timestamps: list[int],
    start_timestamp: int,
    end_timestamp: int,
    prices: list[float],
) -> list[float]:
    if len(timestamps) / ((end_timestamp - start_timestamp) // 60) < .9:
        logging.warning(
            'number of missing data is too high, required: %d, got: %d',
            ((end_timestamp - start_timestamp) // 60),
            len(timestamps),
        )
    # Add missing points before start
    if start_timestamp < timestamps[0]:
        num_points = (timestamps[0] - start_timestamp) // 60
        for i in range(num_points, 0, -1):
            timestamps.insert(0, timestamps[0] - 60)
            prices.insert(0, prices[0])  # Assume price before is same as first known

    # Add missing points after end
    if end_timestamp > timestamps[-1]:
        num_points = (end_timestamp - timestamps[-1]) // 60
        for i in range(1, num_points + 1):
            timestamps.append(timestamps[-1] + 60)
            prices.append(prices[-1])  # Assume price after is same as last known

    # Now interpolate between gaps
    filled_timestamps = []
    filled_prices = []

    for i in range(len(timestamps) - 1):
        t1, t2 = timestamps[i], timestamps[i + 1]
        p1, p2 = prices[i], prices[i + 1]

        filled_timestamps.append(t1)
        filled_prices.append(p1)

        current = t1 + 60
        while current < t2:
            ratio = (current - t1) / (t2 - t1)
            interpolated_price = p1 + ratio * (p2 - p1)

            filled_timestamps.append(current)
            filled_prices.append(interpolated_price)
            current += 60

    filled_timestamps.append(timestamps[-1])
    filled_prices.append(prices[-1])

    return filled_timestamps, filled_prices


def get_prices(
    exchange: Exchange,
    base: Asset,
    quote: Asset,
    from_datetime: datetime.datetime,
    to_datetime: datetime.datetime,
) -> list[float]:
    db = get_db()
    candles = db.query(
        Candle.timestamp,
        Candle.close_price,
    ).filter(
        *[
            Candle.resolution == datetime.timedelta(minutes=1),
            Candle.base_asset == base.value,
            Candle.quote_asset == quote.value,
            Candle.exchange == exchange.value,
            Candle.timestamp >= from_datetime,
            Candle.timestamp <= to_datetime,
        ],
    ).order_by(Candle.timestamp).all()
    candles = list(map(
        lambda c: (int(c[0].timestamp()), float(c[1])),
        candles,
    ))
    timestamps, prices = zip(*candles)
    return _fix_missing_prices(
        list(timestamps),
        int(from_datetime.timestamp()),
        int(to_datetime.timestamp()),
        list(prices),
    )
