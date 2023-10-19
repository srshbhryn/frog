import dataclasses

from frog.utils import msgpack
from frog.types import Amount, Price


@dataclasses.dataclass(slots=True)
class Entry:
    price: Price
    amount: Amount

    @classmethod
    def encoder(cls, instance):
        return msgpack.dumps(
            {
                'price': instance.price,
                'amount': instance.amount,
            }
        )


msgpack.register(Entry, Entry.encoder)


@dataclasses.dataclass(slots=True)
class Book:
    asks: list[Entry]
    bids: list[Entry]

    @classmethod
    def encoder(cls, instance):
        return msgpack.dumps(
            {
                'asks': instance.asks,
                'bids': instance.bids,
            }
        )


msgpack.register(Book, Book.encoder)
