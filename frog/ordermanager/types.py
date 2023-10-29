import dataclasses
import enum
import threading
from typing import NewType, Optional

from frog.square.rpc import RpcService
from frog.types import Amount, Pair, Price, Side
from frog.utils import msgpack


class OrderStatus(msgpack.Enum):
    queued = 0
    placed = 1
    filled = 2
    canceled = 3  # also failed


@msgpack.dataclass
class Order:
    pair: Pair
    side: Side
    amount: Amount
    price: Optional[Price] = None
    status: Optional[OrderStatus] = OrderStatus.queued
    filled_amount: Optional[Amount] = Amount('0')


@msgpack.dataclass
class Position:
    side: Side
    amount: Amount


OrderId = NewType('OrderId', int)


class OrderManger(RpcService):
    def __init__(self) -> None:
        super().__init__()

    def run_server(self) -> None:
        threading.Thread(target=self._fill_collector_process, daemon=True).start()
        super().run_server()

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
