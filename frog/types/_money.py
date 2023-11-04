from typing import Union, Callable

from decimal import Decimal, ROUND_DOWN, Context


context = Context(prec=32 + 16)


class _BaseMoney:
    _type_to_mul_type_map: dict[Callable, Callable] = {}
    _type_to_truediv_type_map: dict[Callable, Callable] = {}

    def __init__(self, value: Union[Decimal, float, int, str]) -> None:
        def quantize(val):
            assert isinstance(val, Decimal)

            return val.quantize(Decimal('1E-16'), rounding=ROUND_DOWN, context=context)

        if isinstance(value, Decimal):
            self._value = quantize(value)
            return

        if isinstance(value, (float, int)):
            self._value = quantize(Decimal(str(value)))
            return

        if isinstance(value, str):
            self._value = quantize(Decimal(value))
            return

        raise NotImplementedError

    def encode(self):
        return (self._value,)

    def as_decimal(self):
        return self._value

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, self.__class__):
            raise NotImplementedError
        return self._value == __value._value

    def __neg__(self):
        return self.__class__(-self._value)

    def __add__(self, __value):
        if not isinstance(__value, self.__class__):
            raise NotImplementedError

        return self.__class__(self._value + __value._value)

    def __sub__(self, __value):
        if not isinstance(__value, self.__class__):
            raise NotImplementedError

        return self + -__value

    def __lt__(self, __value):
        if not isinstance(__value, self.__class__):
            raise NotImplementedError

        return self._value.__lt__(__value._value)

    def __gt__(self, __value):
        if not isinstance(__value, self.__class__):
            raise NotImplementedError

        return self._value.__gt__(__value._value)

    def __repr__(self) -> str:
        return repr(self._value).replace('Decimal', self.__class__.__name__)

    def __str__(self) -> str:
        return str(self._value)

    def __rmul__(self, __value):
        return self.__mul__(__value)

    def __mul__(self, __value):
        if isinstance(__value, (Decimal, int)):
            return self.__class__(self._value * __value)

        if isinstance(__value, (float, str)):
            return self.__class__(self._value * Decimal(str(__value)))

        if isinstance(__value, self.__class__):
            return self._value * __value._value

        for tp, fun in self.__class__._type_to_mul_type_map.items():
            if isinstance(__value, tp()):
                return fun(self, __value)
        raise NotImplementedError

    def __truediv__(self, __value):
        if isinstance(__value, (Decimal, int)):
            return self.__class__(self._value / __value)

        if isinstance(__value, (float, str)):
            return self.__class__(self._value / Decimal(str(__value)))

        if isinstance(__value, self.__class__):
            return self._value / __value._value

        for tp, fun in self.__class__._type_to_truediv_type_map.items():
            if isinstance(__value, tp()):
                return fun(self, __value)
        raise NotImplementedError


class Price(_BaseMoney):
    _type_to_mul_type_map = {
        lambda: Amount: lambda self, u: Value(self.as_decimal() * u.as_decimal()),
    }


class Amount(_BaseMoney):
    _type_to_mul_type_map = {
        lambda: Price: lambda self, u: Value(self.as_decimal() * u.as_decimal()),
    }


class Value(_BaseMoney):
    _type_to_truediv_type_map = {
        lambda: Amount: lambda self, u: Price(self.as_decimal() / u.as_decimal()),
        lambda: Price: lambda self, u: Amount(self.as_decimal() / u.as_decimal()),
    }
