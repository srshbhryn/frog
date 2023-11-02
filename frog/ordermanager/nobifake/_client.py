import logging
import threading

import zmq

from frog import config

from frog.ordermanager.types import OrderManger, OrderId, Order, Pair, OrderStatus, Side, Fill
from frog.square.rpc import RpcService
from frog.utils import msgpack
from frog.utils.shortcuts import get_zmq_context
from frog.types import Amount, Value, Asset
from frog.tradecollector import Trade


class FakeOms(OrderManger):
    FEE_FACTOR = 0.999

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._order_id_to_order_map: dict[OrderId, Order] = {}
        self._next_order_id = 0
        self._asset_to_orderbook_snapshot_map: dict[Asset, Amount] = {}
        self._quote_asset_balance = Value('10_000_000_0')
        self._quote_asset = Asset.RLS
        self._asset_to_position_amount_map: dict[Asset, Amount] = {}
        super().__init__()

    def _add_to_position(self, asset: Asset, amount: Amount):
        if not asset in self._asset_to_position_amount_map:
            self._asset_to_position_amount_map[asset] = Amount(0)
        self._asset_to_position_amount_map[asset] += amount

    def run_server(self) -> None:
        threading.Thread(target=self._background, args=(self._lock,), daemon=True).start()
        threading.Thread(target=self._reporter, args=(self._lock,), daemon=True).start()
        return super().run_server()

    def _fill_collector_process(self) -> None:
        return None

    def _reporter(self, lock: threading.Lock):
        pass

    def _background(self, lock: threading.Lock):
        subscribe_socket: zmq.Socket = get_zmq_context().socket(zmq.SUB)
        subscribe_socket.subscribe('')
        subscribe_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')

        publish_socket: zmq.Socket = get_zmq_context().socket(zmq.PUB)
        publish_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XSUB_PORT}')

        while True:
            try:
                data = subscribe_socket.recv_multipart()
                topic = data[0].decode()
                if topic.startswith('trade'):
                    topic_type = 'trade'

                elif topic.startswith('order'):
                    topic_type = 'order'
                else:
                    continue
                pair = Pair.get_from_str(topic.replace(topic_type, ''))
                if pair.quote != self._quote_asset:
                    continue
                if topic_type == 'trade':
                    with lock:
                        self._update_orders(publish_socket, msgpack.loads(data[1]))
                else:  # topic_type == 'order'
                    self._asset_to_orderbook_snapshot_map[pair.base] = msgpack.loads(data[1])

            except:
                logging.exception('Error In nobifake')

    def _update_orders(self, publish_socket: zmq.Socket, trade: Trade):
        def _get_order():
            for order_id, order in self._order_id_to_order_map.items():
                assert order.price is not None
                if not (order.pair == trade.pair and (order.status not in (OrderStatus.FILLED, OrderStatus.CANCELED))):
                    continue
                if (order.side == Side.LONG and order.price > trade.price) or (
                    order.side == Side.SHORT and order.price < trade.price
                ):
                    return order_id, order
            return None, None

        order_id, order = _get_order()
        if order is None:
            return
        effective_amount = min(trade.amount, order.amount - order.filled_amount)
        order.filled_amount += effective_amount
        if order.filled_amount == order.amount:
            order.status = OrderStatus.FILLED

        if order.side == Side.LONG:
            self._add_to_position(order.pair.base, effective_amount * self.FEE_FACTOR)

        elif order.side == Side.SHORT:
            self._quote_asset_balance += trade.price * effective_amount * self.FEE_FACTOR

        else:
            raise ValueError

        publish_socket.send_multipart(
            (
                f'fill_{order.pair}'.encode(),
                Fill(order_id, effective_amount),
            )
        )

    def _get_next_order_id(self) -> OrderId:
        self._next_order_id += 1
        return OrderId(self._next_order_id)

    @RpcService.register
    def place_order(self, order: Order) -> OrderId:
        # For now, only supporting limit orders
        assert order.price is not None
        with self._lock:
            order_id = self._get_next_order_id()
            self._order_id_to_order_map[order_id] = order
            if order.side == Side.SHORT:
                self._add_to_position(order.pair.base, -order.amount)

            elif order.side == Side.LONG:
                self._quote_asset_balance += -order.amount * order.price
            else:
                raise ValueError

        return order_id

    @RpcService.register
    def cancel_order(self, order_id: OrderId) -> None:
        with self._lock:
            order = self._order_id_to_order_map.get(order_id)
            if order is None or order.status in (OrderStatus.QUEUED, OrderStatus.PLACED):
                return
            assert order.price is not None
            order.status = OrderStatus.CANCELED
            unfilled_amount = order.amount - order.filled_amount
            if order.side == Side.LONG:
                releasing_value = unfilled_amount / order.price
                assert isinstance(releasing_value, Value)
                self._quote_asset_balance += releasing_value
            elif order.side == Side.SHORT:
                self._add_to_position(order.pair.base, unfilled_amount)
            else:
                raise ValueError

    @RpcService.register
    def get_order(self, order_id: OrderId) -> Order:
        return self._order_id_to_order_map[order_id]
