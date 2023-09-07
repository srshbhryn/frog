from frog.ordermanager import types
from frog.ordermanager.types import Order, OrderId, OrderStore, Position
from frog.types import Amount, Pair
from frog.utils.rpc import ZmqRpc


class OrderManager(types.OrderManger):
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
