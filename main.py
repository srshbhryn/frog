import time
import logging

from frog.state import Position, Ticker, State, init as init_state
from frog.config import Config, load as load_config
from frog.prices import get_prices
from frog.residual import get_residual
from frog.core import Core


def init():
    init_state()
    load_config()


def main():
    while True:
        State.ticker = Ticker.current()
        long_asset_prices = get_prices(Config.long_symbol)
        short_asset_prices = get_prices(Config.short_symbol)
        residual = get_residual(long_asset_prices, short_asset_prices)
        logging.info(f'residual is {residual}')
        if State.position == Position.CLOSE:
            if residual < -Config.alpha_open:
                Core.open_long(long_asset_prices[-1], short_asset_prices[-1])
                State.position = Position.LONG
            elif residual > Config.alpha_open:
                Core.open_short(long_asset_prices[-1], short_asset_prices[-1])
                State.position = Position.SHORT

        elif State.position == Position.SHORT:
            if residual < Config.alpha_close:
                Core.close_short(long_asset_prices[-1], short_asset_prices[-1])
                State.position = Position.CLOSE

        elif State.position == Position.LONG:
            if residual > -Config.alpha_close:
                Core.close_long(long_asset_prices[-1], short_asset_prices[-1])
                State.position = Position.CLOSE

        while Ticker.current() == State.ticker:
            time.sleep(1)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(module)s %(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    init()
    main()
