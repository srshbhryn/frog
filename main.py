import time
import enum

from frog.trader import Trader
from frog.types import State, Position, Ticker, Config



def main():
    State.position = Position.CLOSE
    State.ticker = Ticker.current()
    while True:
        long_asset_prices = get_prices(Config.long_symbol)
        short_asset_prices = get_prices(Config.short_symbol)
        residual = get_residual(long_asset_prices, short_asset_prices)
        if State.position == Position.CLOSE:
            if residual > Config.alpha_open:
                open_long(long_asset_prices[-1], short_asset_prices[-1])
            elif residual < -Config.alpha_open:
                open_short(long_asset_prices[-1], short_asset_prices[-1])

        elif State.position == Position.LONG:
            if residual < Config.alpha_close:
                close_long(long_asset_prices[-1], short_asset_prices[-1])

        elif State.position == Position.SHORT:
            if residual > -Config.alpha_close:
                close_short(long_asset_prices[-1], short_asset_prices[-1])

        while Ticker.current() == State.ticker:
            time.sleep(1)
