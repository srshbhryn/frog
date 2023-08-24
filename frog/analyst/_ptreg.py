import functools
from datetime import datetime

import numpy as np
from sklearn.linear_model import LinearRegression  # type: ignore

from frog.tradestore import rpc
from frog.types import Pair, Price, Regression

_client = rpc.Client()

@functools.lru_cache(maxsize=10 * 2 ** 10)
def get_linear_regression(
    long_pair: Pair,
    short_pair: Pair,
    start_time: datetime,
    end_time: datetime,
) -> Regression:
    long_prices = _client.get_timerange_price(long_pair, start_time, end_time)
    short_prices = _client.get_timerange_price(short_pair, start_time, end_time)
    avg_long_price = sum(long_prices.values(), Price(0)) / len(long_prices)
    avg_short_price = sum(short_prices.values(), Price(0)) / len(short_prices)
    long_price_timestamps = set(long_prices.keys())
    short_price_timestamps = set(short_prices.keys())
    timestamps_intersection_set = long_price_timestamps.intersection(
        short_price_timestamps,
    )
    if (
        len(timestamps_intersection_set) > len(short_price_timestamps) / 2
        and len(timestamps_intersection_set) > len(long_price_timestamps) / 2
    ):
        long_returns = []
        short_returns = []
        timestamps_intersection = list(timestamps_intersection_set)
        timestamps_intersection.sort()
        first_ts = timestamps_intersection[0]
        for ts in timestamps_intersection:
            long_returns.append(long_prices[ts] / long_prices[first_ts])
            short_returns.append(short_prices[ts] / short_prices[first_ts])
    else:
        long_returns = []
        short_returns = []

    regression = LinearRegression().fit(
        np.array([[1, p] for p in short_returns]),
        np.array(long_returns),
    )
    alpha = regression.predict([[1, 0]])[0]
    beta = regression.predict([[1, 1]])[0] - alpha
    return Regression(alpha, beta, avg_long_price, avg_short_price)
