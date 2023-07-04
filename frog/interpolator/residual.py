import time
import logging
from multiprocessing import Queue

import numpy as np
from sklearn.linear_model import LinearRegression

from ..types import Interpolation
from ..state import Ticker
from ..config import Config

from .prices import get_prices


def get_interpolation(long_prices, short_prices) -> Interpolation:
    long_returns = [p / long_prices[0] for p in long_prices]
    short_returns = [p / short_prices[0] for p in short_prices]
    reg = LinearRegression().fit(
        np.array([[1, p] for p in short_returns]),
        np.array(long_returns),
    )
    return Interpolation(
        reg=reg,
        long_price_zero=long_prices[0],
        short_price_zero=short_prices[0],
    )


def main(store_queue: Queue):
    ticker = Ticker.current()
    while True:
        long_asset_prices = get_prices(Config.long_symbol)
        short_asset_prices = get_prices(Config.short_symbol)
        logging.debug('fetched prices')
        interpolation = get_interpolation(
            long_asset_prices, short_asset_prices
        )
        store_queue.get()
        store_queue.put(interpolation)
        logging.debug(interpolation)
        logging.debug('interpolation is begin set.')

        while Ticker.current() == ticker:
            time.sleep(1)
        ticker = Ticker.current()
