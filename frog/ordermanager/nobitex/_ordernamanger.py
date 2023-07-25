import logging

from ._client import Trader, MarketTrader

from frog.types import Pair, Amount, Price
from frog.ordermanager._base import OrderManger, ZmqRpc, Order, OrderId, OrderMangerError, OrderStore, Position

class NobitexOrderManager(OrderManger):

    pair_to_open_order_store_map: dict[Pair, OrderStore] = {}
    pair_to_position_map: dict[Pair, Position] = {}

    _order_queue = []

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
