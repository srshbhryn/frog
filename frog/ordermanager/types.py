import dataclasses
import threading
from typing import NewType, Optional

from frog.square.rpc import RpcService
from frog.types import Amount, Pair, Price, Side
from frog.utils import msgpack


OrderId = NewType('OrderId', int)


class OrderStatus(msgpack.Enum):
    QUEUED = 0
    PLACED = 1
    FILLED = 2
    CANCELED = 3  # also known as failed


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Order:
    pair: Pair
    side: Side
    amount: Amount
    price: Optional[Price] = None
    status: OrderStatus = OrderStatus.QUEUED
    filled_amount: Amount = Amount('0')

@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Position:
    side: Side
    amount: Amount


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Fill:
    order_id: OrderId
    amount: Amount


class OrderManger(RpcService):

    def run_server(self) -> None:
        threading.Thread(target=self._fill_collector_process, daemon=True).start()
        super().run_server()

    def _fill_collector_process(self) -> None:
        raise NotImplementedError

    @RpcService.register
    def place_order(self, pair: Pair, side: Side, amount: Amount, price: Price) -> OrderId:
        raise NotImplementedError

    @RpcService.register
    def cancel_order(self, order_id: OrderId) -> None:
        raise NotImplementedError

    @RpcService.register
    def get_order(self, order_id: OrderId) -> Order:
        raise NotImplementedError
