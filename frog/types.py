import enum
import time

from frog.trader import Trader


class Position(enum.Enum):
    SHORT = -1
    CLOSE = 0
    LONG = 1


class Ticker(int):

    @classmethod
    def current(cls) -> 'Ticker':
        return Ticker(int(time.time() / 60) * 60)
