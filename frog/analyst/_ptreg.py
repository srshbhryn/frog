import functools

import numpy as np
from sklearn.linear_model import LinearRegression

from frog.tradestore import PriceServiceClient


_client = PriceServiceClient()


@functools.lru_cache(maxsize=10 * 2 ** 10)
def get_linear_regression(long_symbol, short_symbol, start_time, end_time):
    long_prices = _client.get_timerange_price(long_symbol, start_time, end_time)
    short_prices = _client.get_timerange_price(short_symbol, start_time, end_time)
    avg_long_price = sum(long_prices) / len(long_prices)
    avg_short_price = sum(short_prices) / len(short_prices)
    long_price_timestamps = set(long_prices.keys())
    short_price_timestamps = set(short_prices.keys())
    timestamps_intersection = long_price_timestamps.intersection(short_price_timestamps)
    if  len(timestamps_intersection) > len(short_price_timestamps) / 2 and len(timestamps_intersection) > len(long_price_timestamps) / 2:
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
    regression.avg_long_price = avg_long_price
    regression.avg_short_price = avg_short_price
    return regression


def get_residual(
    long_symbol,
    short_symbol,
    start_time,
    end_time,
    current_long_price,
    current_short_price,
):
    regression = get_linear_regression(long_symbol, short_symbol, start_time, end_time)
    return current_long_price / regression.avg_long_price - regression.predict(
        [1, current_short_price / regression.avg_short_price]
    )[0]
