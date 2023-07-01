import enum
import time

from frog.trader import Trader


class Config:
    alpha_open: float = .004
    alpha_close: float = .001
    long_symbol: str = 'btc-rls'
    short_symbol: str = 'eth-rls'
    beta: float = 1
    usable_total_quote_rate: float = .2


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
