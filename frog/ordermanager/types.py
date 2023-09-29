import dataclasses
import enum
import threading
from typing import NewType, Optional

from frog.square.rpc import RpcService
from frog.types import Amount, Pair, Price, Side
from frog.utils import msgpack


class OrderStatus(enum.Enum):
    queued = 0
    placed = 1
    filled = 2
    canceled = 3  # also failed

    @staticmethod
    def encoder(instance: 'OrderStatus') -> bytes:
        return str(instance.value).encode()

    @staticmethod
    def decoder(data: bytes) -> 'OrderStatus':
        value = int(data.decode())
        for asset in OrderStatus:
            if value == asset.value:
                return asset
        raise Exception('Cant decode order status.')


msgpack.register(OrderStatus, OrderStatus.encoder, OrderStatus.decoder)


@dataclasses.dataclass
class Order:
    pair: Pair
    side: Side
    amount: Amount
    price: Optional[Price] = None
    status: Optional[OrderStatus] = OrderStatus.queued
    filled_amount: Optional[Amount] = Amount('0')

    @staticmethod
    def encoder(instance: 'Order') -> bytes:
        return msgpack.dumps(
            {
                'pair': instance.pair,
                'side': instance.side,
                'amount': instance.amount,
                'price': instance.price,
                'status': instance.status,
                'filled_amount': instance.filled_amount,
            },
        )


msgpack.register(Order, Order.encoder)


@dataclasses.dataclass
class Position:
    side: Side
    amount: Amount

    @staticmethod
    def encoder(instance: 'Position') -> bytes:
        return msgpack.dumps(
            {
                'side': instance.side,
                'amount': instance.amount,
            },
        )


msgpack.register(Position, Position.encoder)


OrderId = NewType('OrderId', int)


class OrderManger(RpcService):
    def __init__(self) -> None:
        super().__init__()

    def _run_server(self) -> None:
        threading.Thread(target=self._fill_collector_process, daemon=True)
        super()._run_server()

    def _fill_collector_process(self) -> None:
        raise NotImplementedError

    @RpcService.register
    def place_order(self, order: Order) -> None:
        raise NotImplementedError

    @RpcService.register
    def cancel_order(self, order_id: OrderId) -> None:
        raise NotImplementedError

    @RpcService.register
    def get_order(self, order_id: OrderId) -> Order:
        raise NotImplementedError
