import dataclasses
import decimal
import enum
from decimal import Decimal

from typing_extensions import TypeAlias

from frog.utils import msgpack

_Decimal: TypeAlias = Decimal | int


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

    @staticmethod
    def encoder(instance: 'Asset') -> bytes:
        return instance.value.encode()

    @staticmethod
    def decoder(data: bytes) -> 'Asset':
        value = data.decode()
        for asset in Asset:
            if value == asset.value:
                return asset
        raise Exception("Cant decode asset.")


@dataclasses.dataclass(slots=True)
class Pair:
    base: Asset
    quote: Asset

    def __str__(self) -> str:
        return str(self.base) + str(self.quote)

    def  __hash__(self) -> int:
        return hash(self.__str__())

    @staticmethod
    def encoder(instance: 'Pair') -> bytes:
        return msgpack.dumps(
            {
                'base': instance.base,
                'quote': instance.quote,
            },
        )


class Side(enum.Enum):
    SHORT = False
    LONG = True

    def __str__(self) -> str:
        return self.name


class Amount(decimal.Decimal):
    pass


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


class Value(decimal.Decimal):
    pass


@dataclasses.dataclass(slots=True)
class PriceAmountPair:
    price: Price
    amount: Amount

    @staticmethod
    def encoder(instance: 'PriceAmountPair') -> bytes:
        return msgpack.dumps(
            {
                'price': instance.price,
                'amount': instance.amount,
            },
        )


@dataclasses.dataclass(slots=True)
class Regression:
    alpha: Decimal
    beta: Decimal
    long_price_normalizer: Price
    short_price_normalizer: Price

    @staticmethod
    def encoder(instance: 'Regression') -> bytes:
        return msgpack.dumps(
            {
                'alpha': instance.alpha,
                'beta': instance.beta,
                'long_price_normalizer': instance.long_price_normalizer,
                'short_price_normalizer': instance.short_price_normalizer,
            },
        )


msgpack.register(Regression, Regression.encoder)
msgpack.register(PriceAmountPair, PriceAmountPair.encoder)
msgpack.register(Pair, Pair.encoder)
msgpack.register(Asset, Asset.encoder, Asset.decoder)
