import datetime

import matplotlib.pyplot as plt

import numpy as np

from frog.types import Pair, Asset

from tadpoles.prices.oracle import Oracle
from tadpoles.types import Exchange
from tadpoles.pairtrading.regression import get_linear_regression


def main():
    quote_asset = Asset.RLS
    target_asset = Asset.ETH
    index_asset = Asset.DOGE
    target_asset_price_oracle = Oracle(Exchange.NOBITEX, Pair(target_asset, quote_asset))
    index_asset_price_oracle = Oracle(Exchange.NOBITEX, Pair(index_asset, quote_asset))
    an_instance = datetime.datetime(2023, 1, 12)
    a_time_period = datetime.timedelta(hours=24)

    target_asset_returns = target_asset_price_oracle.get_timerange_returns(
        an_instance,
        an_instance + a_time_period,
    )
    index_asset_returns = index_asset_price_oracle.get_timerange_returns(
        an_instance,
        an_instance + a_time_period,
    )
    alpha, beta = get_linear_regression(target_asset_returns, index_asset_returns)
    print(alpha, beta)
    timestamps_intersection = set(index_asset_returns.keys()).intersection(
        set(target_asset_returns.keys()),
    )
    residuals = []
    r = 0.0
    for _, ts in enumerate(timestamps_intersection):
        r += float(index_asset_returns[ts] - alpha - beta * target_asset_returns[ts])
        residuals.append(r)
    res_mean = np.mean(residuals)
    res_var = np.mean([(r - res_mean) ** 2 for r in residuals]) ** 0.5

    print(res_mean, res_var)
    x_axis_len = len(residuals)
    x_axis = range(x_axis_len)

    plt.plot(x_axis, [r for r in residuals])
    plt.plot(x_axis, [0] * x_axis_len)
    plt.plot(x_axis, [res_var] * x_axis_len)
    plt.plot(x_axis, [-res_var] * x_axis_len)

    target_asset_returns = target_asset_price_oracle.get_timerange_returns(
        an_instance + a_time_period,
        an_instance + 2 * a_time_period,
    )
    index_asset_returns = index_asset_price_oracle.get_timerange_returns(
        an_instance + a_time_period,
        an_instance + 2 * a_time_period,
    )
    timestamps_intersection = set(index_asset_returns.keys()).intersection(
        set(target_asset_returns.keys()),
    )
    residuals = []
    r = 0.0
    for _, ts in enumerate(timestamps_intersection):
        r += float(index_asset_returns[ts] - alpha - beta * target_asset_returns[ts])
        residuals.append(r)
    plt.plot(x_axis, [r for r in residuals])

    plt.show()


if __name__ == '__main__':
    main()
