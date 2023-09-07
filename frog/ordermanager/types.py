import dataclasses
import enum
from typing import NewType, Optional

from frog.types import Amount, Pair, Price, Side
from frog.utils.rpc import ZmqRpc


@dataclasses.dataclass
class Order:
    side: Side
    amount: Amount
    price: Price


@dataclasses.dataclass
class Position:
    side: Side
    amount: Amount


OrderId = NewType('OrderId', int)
OrderStore = dict[OrderId, Order]


class OrderManger(ZmqRpc):
    def __init__(self) -> None:
        super().__init__()
        self.pair_to_open_order_store_map: dict[Pair, OrderStore] = {}
        self.pair_to_position_map: dict[Pair, Position] = {}

    @ZmqRpc.register
    def place_order(self, pair: Pair, order: Order) -> None:
        raise NotImplementedError

    @ZmqRpc.register
    def cancel_order(self, pair: Pair, order_id: OrderId) -> None:
        raise NotImplementedError

    @ZmqRpc.register
    def get_open_orders_store(self, pair: Pair) -> OrderStore:
        raise NotImplementedError

    @ZmqRpc.register
    def get_position(self, pair: Pair) -> Position:
        raise NotImplementedError

    @ZmqRpc.register
    def get_quote_balance(self) -> Amount:
        raise NotImplementedError
