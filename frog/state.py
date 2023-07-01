import os

from .types import Position, Ticker
from .trader import Trader

class State:
    position: Position
    ticker: Ticker
    trader: Trader


def init():
    State.position = Position.CLOSE
    State.ticker = Ticker.current()
    State.trader = Trader(os.getenv('NOBITEX_AUTH_TOKEN'))
