from decimal import Decimal
import dataclasses
from datetime import datetime
import json

from typing import Union

from frog.utils import msgpack

from ._money import Price, Amount, Value


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

    def __str__(self) -> str:
        return self.value


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Pair:
    base: Asset
    quote: Asset

    def __str__(self) -> str:
        return str(self.base) + str(self.quote)

    def __hash__(self) -> int:
        return hash(self.__str__())

    @staticmethod
    def get_from_str(string: str) -> 'Pair':
        string = string.lower()
        if string[-3:] == 'rls':
            return Pair(Asset(string[:-3]), Asset(string[-3:]))

        if string[-4:] == 'usdt':
            return Pair(Asset(string[:-4]), Asset(string[-4:]))

        raise ValueError


class Side(msgpack.Enum):
    SHORT = '1'
    LONG = '2'

    def __str__(self) -> str:
        return self.name

    def __neg__(self):
        return Side.SHORT if self == Side.LONG else Side.LONG


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

    def __str__(self) -> str:
        return json.dumps(
            {
                'alpha': str(self.alpha),
                'beta': str(self.beta),
                'long_price_normalizer': str(self.long_price_normalizer),
                'short_price_normalizer': str(self.short_price_normalizer),
            }
        )


def datetime_encoder(obj: datetime) -> str:
    return obj.isoformat()


def datetime_decoder(data: str) -> datetime:
    return datetime.fromisoformat(data)


msgpack.register(datetime, datetime_encoder, datetime_decoder)


def decimal_encoder(obj: Decimal) -> str:
    return str(obj)


def decimal_decoder(data: str) -> Decimal:
    return Decimal(data)


msgpack.register(Decimal, decimal_encoder, decimal_decoder)
msgpack.register(Amount)
msgpack.register(Price)
msgpack.register(Value)
