from typing import Union, Callable

from decimal import Decimal, ROUND_DOWN


class _BaseMoney:
    _type_to_mul_type_map: dict[Union[type, tuple[type]], Callable] = {}
    _type_to_truediv_type_map: dict[Union[type, tuple[type]], Callable] = {}
    _type_to_rtruediv_type_map: dict[Union[type, tuple[type]], Callable] = {}

    def __init__(self, value: Union[Decimal, float, int, str]) -> None:
        def quantize(val):
            return val.quantize(Decimal('1E-16'), rounding=ROUND_DOWN)

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
        for tp, fun in self.__class__._type_to_mul_type_map.items():
            if isinstance(__value, tp):
                return fun(self._value)
        raise NotImplementedError

    def __rtruediv__(self, __value):
        for tp, fun in self.__class__._type_to_rtruediv_type_map.items():
            if isinstance(__value, tp):
                return fun(self._value)
        raise NotImplementedError

    def __truediv__(self, __value):
        for tp, fun in self.__class__._type_to_truediv_type_map.items():
            if isinstance(__value, tp):
                return fun(self._value)
        raise NotImplementedError


class Price(_BaseMoney):
    pass


class Amount(_BaseMoney):
    pass


class Value(_BaseMoney):
    pass


_default_mul_map = {
    (Decimal, int): lambda self, u: self.__class__(self.as_decimal() * u),
    (float, str): lambda self, u: self.__class__(self.as_decimal() * Decimal(str(u))),
}
_default_truediv_map = {
    (Decimal, int): lambda self, u: self.__class__(self.as_decimal() / u),
    (float, str): lambda self, u: self.__class__(self.as_decimal() / Decimal(str(u))),
}


Price._type_to_mul_type_map = {
    **_default_mul_map,
    Amount: lambda self, u: Value(self.as_decimal() * u.as_decimal()),
}
Price._type_to_truediv_type_map = _default_truediv_map
Price._type_to_rtruediv_type_map = {
    Value: lambda self, u: Amount(self.as_decimal() * u.as_decimal()),
}


Amount._type_to_mul_type_map = {
    **_default_mul_map,
    Price: lambda self, u: Value(self.as_decimal() * u.as_decimal()),
}
Amount._type_to_truediv_type_map = _default_truediv_map
Amount._type_to_rtruediv_type_map = {
    Value: lambda self, u: Price(self.as_decimal() * u.as_decimal()),
}


Value._type_to_mul_type_map = _default_mul_map
Value._type_to_truediv_type_map = {
    **_default_truediv_map,
    Amount: lambda self, u: Price(self.as_decimal() * u.as_decimal()),
    Price: lambda self, u: Amount(self.as_decimal() * u.as_decimal()),
}
Value._type_to_rtruediv_type_map = {}
