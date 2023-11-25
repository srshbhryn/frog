import dataclasses
import datetime
import decimal

import numpy as np
from sklearn.linear_model import LinearRegression  # type: ignore

from frog.types import Price, Regression


@dataclasses.dataclass(slots=True)
class RegressionDetail:
    number_of_long_prices: int
    number_of_short_prices: int
    number_of_timestamps_intersection_set: int


def get_linear_regression(
    long_prices: dict[datetime.datetime, Price],
    short_prices: dict[datetime.datetime, Price],
) -> tuple[Regression, RegressionDetail]:
    avg_long_price = sum(long_prices.values(), start=Price(0)) / int(len(long_prices))
    avg_short_price = sum(short_prices.values(), start=Price(0)) / int(len(short_prices))
    long_price_timestamps = set(long_prices.keys())
    short_price_timestamps = set(short_prices.keys())
    timestamps_intersection_set = long_price_timestamps.intersection(
        short_price_timestamps,
    )
    regression_detail = RegressionDetail(
        len(long_prices),
        len(short_prices),
        len(timestamps_intersection_set),
    )

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
    alpha = decimal.Decimal(regression.predict([[1, 0]])[0])
    beta = decimal.Decimal(regression.predict([[1, 1]])[0]) - alpha
    return (
        Regression(
            alpha,
            beta,
            avg_long_price,
            avg_short_price,
        ),
        regression_detail,
    )
