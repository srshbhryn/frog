import dataclasses
import datetime
import decimal

import numpy as np
from sklearn.linear_model import LinearRegression  # type: ignore


def get_linear_regression(
    ts_to_long_returns_map: dict[datetime.datetime, decimal.Decimal],
    ts_to_short_returns_map: dict[datetime.datetime, decimal.Decimal],
) -> tuple[decimal.Decimal, decimal.Decimal]:
    long_returns = []
    short_returns = []
    timestamps_intersection = list(
        set(ts_to_long_returns_map.keys()).intersection(
            set(ts_to_short_returns_map.keys()),
        )
    )
    timestamps_intersection.sort()
    for ts in timestamps_intersection:
        long_returns.append(ts_to_long_returns_map[ts])
        short_returns.append(ts_to_short_returns_map[ts])

    regression = LinearRegression().fit(
        np.array([[1, p] for p in short_returns]),
        np.array(long_returns),
    )
    alpha = decimal.Decimal(regression.predict([[1, 0]])[0])
    beta = decimal.Decimal(regression.predict([[1, 1]])[0]) - alpha
    return alpha, beta
