import logging
import functools
from decimal import Decimal
from datetime import datetime

import numpy as np
from sklearn.linear_model import LinearRegression  # type: ignore

from frog.square.rpc import RpcClient
from frog.tradestore import rpc as prices_rpc
from frog.types import Pair, Price, Regression


class Client(RpcClient):
    prices = prices_rpc.Service()


_client = Client().prices

@functools.lru_cache(maxsize=10 * 2 ** 10)
def get_linear_regression(
    long_pair: Pair,
    short_pair: Pair,
    start_time: datetime,
    end_time: datetime,
) -> Regression:
    long_prices = _client.get_timerange_price(long_pair, start_time, end_time)
    short_prices = _client.get_timerange_price(short_pair, start_time, end_time)
    avg_long_price = sum(long_prices.values(), start=Price(0)) / int(len(long_prices))
    assert isinstance(avg_long_price, Price)
    avg_short_price = sum(short_prices.values(), start=Price(0)) / int(len(short_prices))
    assert isinstance(avg_short_price, Price)
    long_price_timestamps = set(long_prices.keys())
    short_price_timestamps = set(short_prices.keys())
    timestamps_intersection_set = long_price_timestamps.intersection(
        short_price_timestamps,
    )
    logging.debug(
        'There are %d long prices, %d short prices and %d of them are in common timestamps.',
        len(long_prices),
        len(short_prices),
        len(timestamps_intersection_set),
    )
    long_log_msg = ','.join([str(ts) for ts in long_price_timestamps])
    short_log_msg = ','.join([str(ts) for ts in short_price_timestamps])
    logging.debug(long_log_msg)
    logging.debug(short_log_msg)

    long_returns = []
    short_returns = []
    timestamps_intersection = list(timestamps_intersection_set)
    timestamps_intersection.sort()
    first_ts = timestamps_intersection[0]
    for ts in timestamps_intersection:
        long_returns.append(long_prices[ts] / long_prices[first_ts])
        short_returns.append(short_prices[ts] / short_prices[first_ts])

    regression = LinearRegression().fit(
        np.array([[1, p] for p in short_returns]),
        np.array(long_returns),
    )
    alpha = Decimal(regression.predict([[1, 0]])[0])
    beta = Decimal(regression.predict([[1, 1]])[0]) - alpha
    return Regression(alpha, beta, avg_long_price, avg_short_price)
