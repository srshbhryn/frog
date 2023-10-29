
from frog.utils import msgpack
from frog.types import Amount, Price


@msgpack.dataclass
class Entry:
    price: Price
    amount: Amount


@msgpack.dataclass
class Book:
    asks: list[Entry]
    bids: list[Entry]

    @classmethod
    def encoder(cls, instance):
        return (instance.asks, instance.bids)
