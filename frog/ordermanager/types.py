import dataclasses
import enum
import threading
from typing import NewType, Optional

from frog.types import Amount, Pair, Price, Side
from frog.utils.rpc import ZmqRpc


class OrderStatus(enum.Enum):
    queued = 0
    placed = 1
    filled = 2
    canceled = 3  # also failed


@dataclasses.dataclass
class Order:
    pair: Pair
    side: Side
    amount: Amount
    price: Optional[Price]
    status = OrderStatus.queued
    filled_amount = Amount('0')


@dataclasses.dataclass
class Position:
    side: Side
    amount: Amount


OrderId = NewType('OrderId', int)


class OrderManger(ZmqRpc):
    def __init__(self) -> None:
        super().__init__()

    def _run_server(self) -> None:
        threading.Thread(target=self._fill_collector_process, daemon=True)
        super()._run_server()

    def _fill_collector_process(self) -> None:
        raise NotImplementedError

    @ZmqRpc.register
    def place_order(self, order: Order) -> None:
        raise NotImplementedError

    @ZmqRpc.register
    def cancel_order(self, order_id: OrderId) -> None:
        raise NotImplementedError

    @ZmqRpc.register
    def get_order(self, order_id: OrderId) -> Order:
        raise NotImplementedError
