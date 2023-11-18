import logging
import threading
import queue

import zmq

from frog import config

from frog.ordermanager.types import (
    OrderManger,
    OrderId,
    Order,
    OrderStatus,
    Fill,
    AccountId,
)
from frog.square.rpc import RpcService
from frog.utils import msgpack
from frog.utils.shortcuts import get_zmq_context
from frog.types import (
    Amount,
    Price,
    Pair,
    Side,
)
from frog.tradecollector import Trade
from frog.bookwatch.types import Book


class Service(OrderManger):
    topic = b'nobifake'

    def __init__(self) -> None:
        super().__init__()
        self._next_order_id = 0
        self._pair_to_orderbook_snapshot_map: dict[Pair, Book] = {}

    def _fill_collector(self, lock: threading.Lock, publish_queue: queue.Queue):
        subscribe_socket: zmq.Socket = get_zmq_context().socket(zmq.SUB)
        subscribe_socket.subscribe('order_')
        subscribe_socket.subscribe('trade_')
        subscribe_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')

        while True:
            try:
                data = subscribe_socket.recv_multipart()
                topic = data[0].decode()
                if topic.startswith('trade_'):
                    topic_type = 'trade_'
                elif topic.startswith('order_'):
                    topic_type = 'order_'
                else:
                    raise ValueError
                pair = Pair.get_from_str(topic.replace(topic_type, ''))
                if topic_type == 'trade_':
                    with lock:
                        _ = self.update_orders(
                            lock,
                            publish_queue,
                            self._create_fill(msgpack.loads(data[1])),
                        )
                else:  # topic_type == 'order'
                    self._pair_to_orderbook_snapshot_map[pair] = msgpack.loads(data[1])

            except:
                logging.exception('Error In nobifake')

    def _create_fill(self, trade: Trade):
        def _get_order_id():
            for order_id, order in self._order_id_to_order_map.items():
                assert order.price is not None
                if any(
                    (
                        order.pair != trade.pair,
                        order.status == OrderStatus.FILLED,
                        order.status == OrderStatus.CANCELED,
                    ),
                ):
                    continue
                if (order.side == Side.LONG and order.price > trade.price) or (
                    order.side == Side.SHORT and order.price < trade.price
                ):
                    return order_id
            return -1

        order_id = _get_order_id()
        return Fill(order_id, trade.amount, trade.price)

    def _get_next_order_id(self) -> OrderId:
        self._next_order_id += 1
        return OrderId(self._next_order_id)

    @RpcService.register
    def place_order(
        self,
        pair: Pair,
        side: Side,
        amount: Amount,
        price: Price,
        **kwargs,
    ) -> OrderId:
        order = Order(pair, side, amount, price)
        with self._lock:
            order_id = self._get_next_order_id()
            self._account_manager.add_order_for_an_account(
                order_id,
                AccountId(kwargs['client_identity']),
            )
            self._order_id_to_order_map[order_id] = order

        return order_id

    @RpcService.register
    def cancel_order(self, order_id: OrderId) -> None:
        with self._lock:
            order = self._order_id_to_order_map.get(order_id)
            if order is None or order.status in (
                OrderStatus.QUEUED,
                OrderStatus.PLACED,
            ):
                return
            assert order.price is not None
            order.status = OrderStatus.CANCELED

    @RpcService.register
    def get_order(self, order_id: OrderId) -> Order:
        return self._order_id_to_order_map[order_id]
