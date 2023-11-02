import dataclasses
from typing import Any, TYPE_CHECKING
from datetime import datetime

from frog.utils import msgpack


def test_1():
    class A:
        def __init__(self, alpha, beta) -> None:
            self.alpha = alpha
            self.beta = beta

        def encode(self):
            return (self.alpha, self.beta)

        @staticmethod
        def decode(data: Any):
            return A(*data)

        def __eq__(self, __value: object) -> bool:
            if not isinstance(__value, A):
                raise NotImplementedError
            return self.alpha == __value.alpha and self.beta == __value.beta

    msgpack.register(A)
    a = A(127, 32343)
    assert a == msgpack.loads(msgpack.dumps(a))


def test_default_decoder():

    class B:
        def __init__(self, x, y) -> None:
            self.x = x
            self.y = y

        def encode(self):
            return (self.x, self.y)

        def __eq__(self, __value: object) -> bool:
            if not isinstance(__value, B):
                raise NotImplementedError
            return self.x == __value.x and self.y == __value.y

    msgpack.register(B)
    b = B('wow', 3234334556)
    assert b == msgpack.loads(msgpack.dumps(b))


def test_dataclass():
    @msgpack.dataclass
    @dataclasses.dataclass(slots=True)
    class C:
        a: int
        b: int

        def __eq__(self, __value: object) -> bool:
            if not isinstance(__value, C):
                raise NotImplementedError
            return self.a == __value.a and self.b == __value.b

    a = C(127, 32343)
    assert a == msgpack.loads(msgpack.dumps(a))


def test_enum():
    class D(msgpack.Enum):
        a = 123
        b = 545

    a = D(123)
    assert a == msgpack.loads(msgpack.dumps(a))


def test_external_type():
    def datetime_encoder(obj: datetime) -> str:
        return obj.isoformat()

    def datetime_decoder(data: str) -> datetime:
        return datetime.fromisoformat(data)

    msgpack.register(datetime, datetime_encoder, datetime_decoder)

    a = datetime.now()
    assert a == msgpack.loads(msgpack.dumps(a))