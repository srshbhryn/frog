import functools
from datetime import datetime
from decimal import Decimal

import numpy as np
from sklearn.linear_model import LinearRegression

from frog import config
from frog.tradestore import rpc
from frog.types import Asset, Interpolation, Pair, Price

_client = rpc.Client()

@functools.lru_cache(maxsize=10 * 2 ** 10)
def get_linear_regression(
    long_symbol: Asset,
    short_symbol: Asset,
    start_time: datetime,
    end_time: datetime,
) -> Interpolation:
    long_prices = _client.get_timerange_price(
        Pair(long_symbol, config.QUOTE),
        start_time,
        end_time,
    )
    short_prices = _client.get_timerange_price(
        Pair(short_symbol, config.QUOTE),
        start_time,
        end_time,
    )
    avg_long_price = sum(long_prices.values()) / len(long_prices)
    avg_short_price = sum(short_prices.values()) / len(short_prices)
    long_price_timestamps = set(long_prices.keys())
    short_price_timestamps = set(short_prices.keys())
    timestamps_intersection = long_price_timestamps.intersection(short_price_timestamps)
    if (
        len(timestamps_intersection) > len(short_price_timestamps) / 2
        and len(timestamps_intersection) > len(long_price_timestamps) / 2
    ):
        long_returns = []
        short_returns = []
        timestamps_intersection = list(timestamps_intersection)
        timestamps_intersection.sort()
        first_ts = timestamps_intersection[0]
        for ts in timestamps_intersection:
            long_returns.append(long_prices[ts] / long_prices[first_ts] )
            short_returns.append(short_prices[ts] / short_prices[first_ts] )
    else:
        long_returns = []
        short_returns = []

    regression = LinearRegression().fit(
        np.array([[1, p] for p in short_returns]),
        np.array(long_returns),
    )
    alpha = regression.predict([[1, 0]])[0]
    beta = regression.predict([[1, 1]])[0] - alpha
    return Interpolation(alpha, beta, avg_long_price, avg_short_price)


def get_residual(
    long_symbol: Asset,
    short_symbol: Asset,
    start_time: datetime,
    end_time: datetime,
    current_long_price: Price,
    current_short_price: Price,
) -> Decimal:
    i = get_linear_regression(
        long_symbol,
        short_symbol,
        start_time,
        end_time,
    )
    normalized_long_price = current_long_price / i.long_price_normalizer
    normalized_short_price = current_short_price / i.short_price_normalizer
    return Decimal(
        normalized_long_price - i.alpha - (i.beta * normalized_short_price),
    )
