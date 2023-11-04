from decimal import Decimal
import dataclasses
from datetime import datetime

from typing import Union

from frog.utils import msgpack


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


class Amount:
    def __init__(self, value: Union[Decimal, float, int, str]) -> None:
        if isinstance(value, Decimal):
            self._value = value
            self._zero_check()
            return

        if isinstance(value, (float, int)):
            self._value = Decimal(str(value))
            self._zero_check()
            return

        if isinstance(value, str):
            self._value = Decimal(value)
            self._zero_check()
            return

        raise NotImplementedError

    def _zero_check(self):
        if self._value < Decimal('0e-20'):
            self._value = Decimal('0')

    def encode(self):
        return (self._value,)

    def as_decimal(self):
        return self._value

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Amount):
            raise NotImplementedError
        return self - __value == Amount('0')

    def __neg__(self):
        return self * (-1)

    def __sub__(self, __value: 'Amount') -> 'Amount':
        return self + -__value

    def __lt__(self, __value: 'Amount'):
        return self._value < __value._value

    def __add__(self, __value: 'Amount') -> 'Amount':
        return Amount(self._value + __value._value)

    def __repr__(self) -> str:
        return self._value.__repr__().replace('Decimal', 'Amount')

    def __mul__(self, __value: Union[Decimal, float, int, 'Price']) -> Union['Amount', 'Value']:
        if isinstance(__value, (Decimal, int)):
            return Amount(self._value.__mul__(__value))

        if isinstance(__value, float):
            return Amount(self._value.__mul__(Decimal(str(__value))))

        if isinstance(__value, Price):
            return Value(self._value * __value._value)

        raise NotImplementedError

    def __truediv__(
        self, __value: Union['Price', 'Value', 'Amount', Decimal, float, int]
    ) -> Union[Decimal, 'Amount', 'Value']:
        if isinstance(__value, (Decimal, int)):
            return Amount(self._value.__truediv__(__value))

        if isinstance(__value, float):
            return Amount(self._value.__truediv__(Decimal(str(__value))))

        if isinstance(__value, Price):
            return Value(self._value.__truediv__(__value._value))

        if isinstance(__value, Amount):
            return self._value.__truediv__(__value._value)

        raise NotImplementedError


class Price:
    def __init__(self, value: Union[Decimal, float, int, str]) -> None:
        if isinstance(value, Decimal):
            self._value = value
            self._zero_check()
            return

        if isinstance(value, (float, int)):
            self._value = Decimal(str(value))
            self._zero_check()
            return

        if isinstance(value, str):
            self._value = Decimal(value)
            self._zero_check()
            return

        raise NotImplementedError

    def _zero_check(self):
        if self._value < Decimal('0e-20'):
            self._value = Decimal('0')

    def encode(self):
        return (self._value,)

    def __neg__(self):
        return self * (-1)

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Price):
            raise NotImplementedError
        return self + -__value == Price('0')

    def __lt__(self, __value: 'Price') -> bool:
        return self._value.__lt__(__value._value)

    def __gt__(self, __value: 'Price') -> bool:
        return __value.__lt__(self)

    def __add__(self, __value: 'Price') -> 'Price':
        return Price(self._value + __value._value)

    def __mul__(self, __value: Union[Amount, Decimal, float, int]) -> Union['Price', 'Value']:
        if isinstance(__value, (Decimal, int)):
            return Price(self._value.__mul__(__value))

        if isinstance(__value, Amount):
            return Value(self._value.__mul__(__value._value))

        if isinstance(__value, float):
            return Price(self._value.__mul__(Decimal(str(__value))))

        raise NotImplementedError

    def __truediv__(self, __value: Union['Price', Decimal, int, float]) -> Union['Price', Decimal]:
        if isinstance(__value, Price):
            r = self._value.__truediv__(__value._value)
            return r

        if isinstance(__value, (Decimal, int)):
            rp = Price(self._value.__truediv__(__value))
            return rp


        if isinstance(__value, float):
            rp = Price(self._value.__truediv__(Decimal(str(__value))))
            return rp

        raise NotImplementedError

    def as_decimal(self):
        return self._value


class Value:
    def __init__(self, value: Union[Decimal, float, int, str]) -> None:
        if isinstance(value, Decimal):
            self._value = value
            self._zero_check()
            return

        if isinstance(value, (float, int)):
            self._value = Decimal(str(value))
            self._zero_check()
            return

        if isinstance(value, str):
            self._value = Decimal(value)
            self._zero_check()
            return

        raise NotImplementedError

    def _zero_check(self):
        if self._value < Decimal('0e-20'):
            self._value = Decimal('0')

    def encode(self):
        return (self._value,)

    def __neg__(self):
        return self * (-1)

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Value):
            raise NotImplementedError
        return self + -__value == Value('0')

    def __add__(self, __value: 'Value') -> 'Value':
        return Value(self._value + __value._value)

    def __mul__(self, __value: Union[Price, Decimal, float, int]) -> Union['Value', Amount]:
        if isinstance(__value, (Decimal, int)):
            return Value(self._value.__mul__(__value))

        if isinstance(__value, float):
            return Value(self._value.__mul__(Decimal(str(__value))))

        if isinstance(__value, Price):
            return Amount(self._value.__mul__(__value._value))

        raise NotImplementedError

    def __truediv__(self, __value: Union['Value', Decimal, float, int, Price]) -> Union[Decimal, 'Value', Amount]:
        if isinstance(__value, (Decimal, int)):
            return Value(self._value.__truediv__(__value))

        if isinstance(__value, Price):
            return Amount(self._value.__truediv__(__value._value))

        if isinstance(__value, float):
            return Value(self._value.__truediv__(Decimal(str(__value))))

        if isinstance(__value, Value):
            return self._value.__truediv__(__value._value)

        raise NotImplementedError

    def __repr__(self) -> str:
        return self._value.__repr__().replace('Decimal', 'Value')

    def as_decimal(self):
        return self._value


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