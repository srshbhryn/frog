import time

from frog.types import Position, Ticker
from frog.state import State, init as init_state
from frog.config import Config, load as load_config
from frog.prices import get_prices
from frog.residual import get_residual
from frog.core import Core


def init():
    init_state()
    load_config()


def main():
    while True:
        long_asset_prices = get_prices(Config.long_symbol)
        short_asset_prices = get_prices(Config.short_symbol)
        residual = get_residual(long_asset_prices, short_asset_prices)
        if State.position == Position.CLOSE:
            if residual > Config.alpha_open:
                Core.open_long(long_asset_prices[-1], short_asset_prices[-1])
            elif residual < -Config.alpha_open:
                Core.open_short(long_asset_prices[-1], short_asset_prices[-1])

        elif State.position == Position.LONG:
            if residual < Config.alpha_close:
                Core.close_long(long_asset_prices[-1], short_asset_prices[-1])

        elif State.position == Position.SHORT:
            if residual > -Config.alpha_close:
                Core.close_short(long_asset_prices[-1], short_asset_prices[-1])

        while Ticker.current() == State.ticker:
            time.sleep(1)
