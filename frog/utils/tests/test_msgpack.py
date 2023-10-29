from typing import Any
from frog.utils import msgpack


class A:
    def __init__(self, alpha, beta) -> None:
        self.alpha = alpha
        self.beta = beta

    @staticmethod
    def encoder(instance: 'A'):
        return msgpack.dumps((instance.alpha, instance.beta))

    @staticmethod
    def decoder(data: Any):
        return A(*msgpack.loads(data))

    def __eq__(self, __value: 'A') -> bool:
        return self.alpha == __value.alpha and self.beta == __value.beta


msgpack.register(A, A.encoder, A.decoder)


def test_1():
    a = A(127, 32343)
    assert a == msgpack.loads(msgpack.dumps(a))
