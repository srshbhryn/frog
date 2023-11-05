import dataclasses

from frog.utils import msgpack
from frog.types import Amount, Price


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Entry:
    price: Price
    amount: Amount

    def __str__(self) -> str:
        return f'{self.price}-{self.amount}'

    def __hash__(self) -> int:
        return hash(str(self))


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Book:
    asks: list[Entry]
    bids: list[Entry]
