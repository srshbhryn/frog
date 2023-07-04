import os
import enum
import time
import decimal

from .trader import Trader, MarketTrader


class Position(enum.Enum):
    SHORT = -1
    CLOSE = 0
    LONG = 1


class Ticker(int):

    @classmethod
    def current(cls) -> 'Ticker':
        return Ticker(int(time.time() / 60) * 60)


class State:
    position: Position
    ticker: Ticker
    trader: Trader


def init():
    State.position = Position.CLOSE
    State.ticker = Ticker.current()
    State.trader = MarketTrader(os.getenv('NOBITEX_AUTH_TOKEN'))
