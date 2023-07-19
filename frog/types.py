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

    def  __str__(self) -> str:
        return self.value


@dataclasses.dataclass(slots=True)
class Pair:
    base: Asset
    quote: Asset

    def __str__(self) -> str:
        return str(self.base) + str(self.quote)

    def  __hash__(self) -> int:
        return hash(self.__str__)


class Side(enum.Enum):
    SHORT = False
    LONG = True

    def __str__(self) -> str:
        return self.name


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
