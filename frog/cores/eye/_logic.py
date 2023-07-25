import enum

from ..base import Core

class Eye(Core):
    class State(enum.Enum):
        close = 1
        long = 2
        short = 3

    class Event(enum.Enum):
        long_trade = 1
        short_trade = 2
        long_orderbook = 11
        short_orderbook = 12
        long_order_fill = 21
        short_order_fill = 22


    class Action(enum.Enum):
        pass
