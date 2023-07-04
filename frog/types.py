import dataclasses
from decimal import Decimal

from sklearn.linear_model import LinearRegression


@dataclasses.dataclass(slots=True)
class Interpolation:
    reg: LinearRegression
    long_price_normalizer: float
    short_price_normalizer: float


@dataclasses.dataclass(slots=True)
class OrderBook:
    short_bid_price: Decimal
    short_ask_price: Decimal
    long_bid_price: Decimal
    long_ask_price: Decimal
