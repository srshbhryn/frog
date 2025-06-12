import datetime
import dataclasses

from frog.types import Asset

from tadpoles.timescaledb import get_db
from tadpoles.types import Exchange
from tadpoles.prices.models import Candle as CandleEntity


@dataclasses.dataclass
class Candle:
    min_price: float
    max_price: float
    open_price: float
    close_price: float


@dataclasses.dataclass
class FixedPrices:
    fixed_timestamps: list[int]
    fixed_prices: list[float]
    number_of_missing_points: int


@dataclasses.dataclass
class FixedCandles:
    fixed_timestamps: list[int]
    fixed_candles: list[Candle]
    number_of_missing_points: int


def _fix_missing_prices(
    timestamps: list[int],
    start_timestamp: int,
    end_timestamp: int,
    prices: list[float],
) -> FixedPrices:
    number_of_missing_points = int(len(timestamps) / ((end_timestamp - start_timestamp) // 60))
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
    return FixedPrices(
        fixed_timestamps=filled_timestamps,
        fixed_prices=filled_prices,
        number_of_missing_points=number_of_missing_points,
    )


def get_prices(
    exchange: Exchange,
    base: Asset,
    quote: Asset,
    from_datetime: datetime.datetime,
    to_datetime: datetime.datetime,
) -> FixedPrices:
    db = get_db()
    candles = db.query(
        CandleEntity.timestamp,
        CandleEntity.close_price,
    ).filter(
        *[
            CandleEntity.resolution == datetime.timedelta(minutes=1),
            CandleEntity.base_asset == base.value,
            CandleEntity.quote_asset == quote.value,
            CandleEntity.exchange == exchange.value,
            CandleEntity.timestamp >= from_datetime,
            CandleEntity.timestamp <= to_datetime,
        ],
    ).order_by(CandleEntity.timestamp).all()
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


def get_candles(
    exchange: Exchange,
    base: Asset,
    quote: Asset,
    from_datetime: datetime.datetime,
    to_datetime: datetime.datetime,
):
    db = get_db()
    candles = db.query(
        CandleEntity.timestamp,
        CandleEntity.close_price,
        CandleEntity.open_price,
        CandleEntity.min_price,
        CandleEntity.max_price,
    ).filter(
        *[
            CandleEntity.resolution == datetime.timedelta(minutes=1),
            CandleEntity.base_asset == base.value,
            CandleEntity.quote_asset == quote.value,
            CandleEntity.exchange == exchange.value,
            CandleEntity.timestamp >= from_datetime,
            CandleEntity.timestamp <= to_datetime,
        ],
    ).order_by(CandleEntity.timestamp).all()
    try:
        timestamps, close_prices, open_prices, min_prices, max_prices = zip(*list(map(
            lambda c: (
                int(c[0].timestamp()),
                float(c[1]),
                float(c[2]),
                float(c[3]),
                float(c[4]),
            ),
            candles,
        )))
    except Exception as e:
        print(e)
    fixed_close_prices = _fix_missing_prices(
        list(timestamps),
        int(from_datetime.timestamp()),
        int(to_datetime.timestamp()),
        list(close_prices),
    )
    fixed_open_prices = _fix_missing_prices(
        list(timestamps),
        int(from_datetime.timestamp()),
        int(to_datetime.timestamp()),
        list(open_prices),
    )
    fixed_min_prices = _fix_missing_prices(
        list(timestamps),
        int(from_datetime.timestamp()),
        int(to_datetime.timestamp()),
        list(min_prices),
    )
    fixed_max_prices = _fix_missing_prices(
        list(timestamps),
        int(from_datetime.timestamp()),
        int(to_datetime.timestamp()),
        list(max_prices),
    )
    return FixedCandles(
        fixed_timestamps=fixed_close_prices.fixed_timestamps,
        fixed_candles=[
            Candle(min_price=min_price, max_price=max_price, open_price=open_price, close_price=close_price)
            for close_price, open_price, min_price, max_price in zip(
                fixed_close_prices.fixed_prices,
                fixed_open_prices.fixed_prices,
                fixed_min_prices.fixed_prices,
                fixed_max_prices.fixed_prices,
            )
        ],
        number_of_missing_points=fixed_close_prices.number_of_missing_points,
    )


def get_min_max_timestamps(
    exchange: Exchange,
    base: Asset,
    quote: Asset,
):
    db = get_db()
    candles = db.query(
        CandleEntity.timestamp,
    ).filter(
        *[
            CandleEntity.resolution == datetime.timedelta(minutes=1),
            CandleEntity.base_asset == base.value,
            CandleEntity.quote_asset == quote.value,
            CandleEntity.exchange == exchange.value,
        ],
    ).order_by(CandleEntity.timestamp).all()
    timestamps = [int(c[0].timestamp()) for c in candles]
    return min(timestamps), max(timestamps)
