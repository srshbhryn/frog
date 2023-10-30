import dataclasses
from datetime import datetime
import decimal
from decimal import Decimal

from typing_extensions import TypeAlias

from frog.utils import msgpack

_Decimal: TypeAlias = Decimal | int


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class OrderBook:
    short_bid_price: Decimal
    short_ask_price: Decimal
    long_bid_price: Decimal
    long_ask_price: Decimal



class Asset(msgpack.Enum):
    RLS = 'rls'
    USDT = 'usdt'
    BTC = 'btc'
    ETH = 'eth'
    DOGE = 'doge'
    SHIB = 'shib'

    def  __str__(self) -> str:
        return self.value


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Pair:
    base: Asset
    quote: Asset

    def __str__(self) -> str:
        return str(self.base) + str(self.quote)

    def  __hash__(self) -> int:
        return hash(self.__str__())


class Side(msgpack.Enum):
    SHORT = b'1'
    LONG = b'2'

    def __str__(self) -> str:
        return self.name


class Amount(decimal.Decimal):
    def __repr__(self) -> str:
        return super().__repr__().replace('Decimal', 'Amount')


class Price(decimal.Decimal):
    def __add__(self, __value: _Decimal) -> 'Price':
        return Price(super().__add__(__value))

    def __truediv__(self, __value: _Decimal | float) -> 'Price':
        if isinstance(__value, float):
            return Price(super().__truediv__(Decimal(str(__value))))
        return Price(super().__sub__(__value))

    def __mul__(self, __value: _Decimal | float) -> 'Price':
        if isinstance(__value, float):
            return Price(super().__mul__(Decimal(str(__value))))
        return Price(super().__mul__(__value))

    def __repr__(self) -> str:
        return super().__repr__().replace('Decimal', 'Price')


class Value(decimal.Decimal):
    pass


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class PriceAmountPair:
    price: Price
    amount: Amount


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Regression:
    alpha: Decimal
    beta: Decimal
    long_price_normalizer: Price
    short_price_normalizer: Price

def datetime_encoder(obj: datetime) -> bytes:
    return obj.isoformat().encode()


def datetime_decoder(data: bytes) -> datetime:
    return datetime.fromisoformat(data.decode())


msgpack.register(datetime, datetime_encoder, datetime_decoder)


def decimal_encoder(obj: Decimal) -> bytes:
    return str(obj).encode()


def decimal_decoder(data: bytes) -> Decimal:
    return Decimal(data.decode())


def price_encoder(obj: Price) -> bytes:
    return str(obj).encode()


def price_decoder(data: bytes) -> Price:
    return Price(data.decode())


def amount_encoder(obj: Amount) -> bytes:
    return str(obj).encode()


def amount_decoder(data: bytes) -> Amount:
    return Amount(data.decode())


msgpack.register(Price, decimal_encoder, decimal_decoder)
msgpack.register(Amount, decimal_encoder, decimal_decoder)
msgpack.register(Decimal, decimal_encoder, decimal_decoder)
