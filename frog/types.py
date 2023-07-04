import dataclasses
from decimal import Decimal


@dataclasses.dataclass(slots=True)
class Interpolation:
    alpha: float
    beta: float
    long_price_zero: float
    short_price_zero: float


@dataclasses.dataclass(slots=True)
class OrderBook:
    short_bid_price: Decimal
    short_ask_price: Decimal
    long_bid_price: Decimal
    long_ask_price: Decimal
