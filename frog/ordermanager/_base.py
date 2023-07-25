import enum
import dataclasses

from typing import Optional, NewType

from frog.types import Pair, Amount, Price
from frog.utils.rpc import ZmqRpc


class OrderMangerError(enum.Enum):
    pass


@dataclasses.dataclass
class Order:
    is_long: bool
    amount: Amount
    price: Optional[Price]


@dataclasses.dataclass
class Position:
    is_long: bool
    amount: Amount


OrderId = NewType('OrderId', int)
OrderStore = dict[OrderId, Order]


class OrderManger(ZmqRpc):

    pair_to_open_order_store_map: dict[Pair, OrderStore] = {}
    pair_to_position_map: dict[Pair, Position] = {}

    @ZmqRpc.register
    def place_order(self, pair: Pair, order: Order) -> None:
        raise NotImplementedError

    @ZmqRpc.register
    def cancel_order(self, pair: Pair, order_id: OrderId) ->  None:
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
