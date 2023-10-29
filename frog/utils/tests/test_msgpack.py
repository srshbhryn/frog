from typing import Any
from frog.utils import msgpack


def test_1():
    @msgpack.register
    class A:
        def __init__(self, alpha, beta) -> None:
            self.alpha = alpha
            self.beta = beta

        def encode(self):
            return (self.alpha, self.beta)

        @staticmethod
        def decode(data: Any):
            return A(*data)

        def __eq__(self, __value: 'A') -> bool:
            return self.alpha == __value.alpha and self.beta == __value.beta

    a = A(127, 32343)
    assert a == msgpack.loads(msgpack.dumps(a))


def test_default_decoder():

    @msgpack.register
    class B:
        def __init__(self, x, y) -> None:
            self.x = x
            self.y = y

        def encode(self):
            return (self.x, self.y)

        def __eq__(self, __value: 'B') -> bool:
            return self.x == __value.x and self.y == __value.y


    b = B('wow', 3234334556)
    assert b == msgpack.loads(msgpack.dumps(b))


def test_dataclass():
    @msgpack.dataclass
    class C:
        a: int
        b: int

    def __eq__(self, __value: 'C') -> bool:
        return self.a == __value.a and self.b == __value.b

    a = C(127, 32343)
    assert a == msgpack.loads(msgpack.dumps(a))


def test_enum():
    class D(msgpack.Enum):
        a = 123
        b = 545

    a = D(123)
    assert a == msgpack.loads(msgpack.dumps(a))
