import typing
import enum
import decimal
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



class Asset(enum.Enum):
    RLS = 'rls'
    USDT = 'usdt'
    BTC = 'btc'
    ETH = 'eth'
    DOGE = 'doge'
    SHIB = 'shib'


Pair = tuple[Asset, Asset]


class Side(enum.Enum):
    SHORT = False
    LONG = True


class Amount(decimal.Decimal):
    pass


class Price(decimal.Decimal):
    pass


class Value(decimal.Decimal):
    pass


@dataclasses.dataclass(slots=True)
class PriceAmountPair:
    price: Price
    amount: Amount
