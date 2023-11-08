import logging
import time
import threading

import zmq

from frog import config

from frog.ordermanager.types import OrderManger, OrderId, Order, Pair, OrderStatus, Side, Fill
from frog.square.rpc import RpcService
from frog.utils import msgpack
from frog.utils.shortcuts import get_zmq_context
from frog.types import Amount, Value, Asset, Price
from frog.tradecollector import Trade
from frog.bookwatch.types import Book


class Service(OrderManger):
    topic = b'nobifake'
    FEE_FACTOR = 0.999

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._order_id_to_order_map: dict[OrderId, Order] = {}
        self._next_order_id = 0
        self._asset_to_orderbook_snapshot_map: dict[Asset, Book] = {}
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
        def get_asset_price(asset):
            book = self._asset_to_orderbook_snapshot_map.get(asset)
            if book is None or len(book.asks) == 0 or len(book.bids) == 0:
                return None
            return (book.asks[0].price + book.bids[0].price) / 2

        while True:

            def _():
                account_value = self._quote_asset_balance
                for asset, pos in self._asset_to_position_amount_map.items():
                    price = get_asset_price(asset)
                    if price is None:
                        logging.info(
                            'cant compute account value, %s price is not available.',
                            str(asset),
                        )
                        return
                    value = pos * price
                    assert isinstance(value, Value)
                    account_value += value
                    logging.info('%s position amount: %s', str(asset), str(pos))

                logging.info('Account value, %s', str(account_value))
                for order in self._order_id_to_order_map.values():
                    if order.status in (
                        OrderStatus.CANCELED,
                        OrderStatus.FILLED,
                    ):
                        continue
                    if order.side == Side.LONG:
                        assert order.price is not None
                        unfilled_amount = order.amount - order.filled_amount
                        blocked_value = unfilled_amount * order.price
                        assert isinstance(blocked_value, Value)
                        logging.info(
                            '%s %s is blocked in %s long order with unfilled amount: %s.',
                            str(blocked_value),
                            str(self._quote_asset),
                            str(order.pair.base),
                            str(unfilled_amount),
                        )

                    elif order.side == Side.SHORT:
                        unfilled_amount = order.amount - order.filled_amount
                        blocked_value = unfilled_amount * get_asset_price(order.pair.base)
                        assert isinstance(blocked_value, Value)
                        logging.info(
                            '%s %s is blocked in short order, current value: %s.',
                            str(unfilled_amount),
                            str(order.pair.base),
                            str(blocked_value),
                        )

                    else:
                        logging.error('invalid side: %s', str(order.side))
            with lock:
                _()
            time.sleep(10)

    def _background(self, lock: threading.Lock):
        subscribe_socket: zmq.Socket = get_zmq_context().socket(zmq.SUB)
        subscribe_socket.subscribe('')
        subscribe_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')

        publish_socket: zmq.Socket = get_zmq_context().socket(zmq.PUB)
        publish_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XSUB_PORT}')

        while True:
            try:
                data = subscribe_socket.recv_multipart()
                assert len(data) > 0
                topic = data[0].decode()
                if topic.startswith('trade_'):
                    topic_type = 'trade_'

                elif topic.startswith('order_'):
                    topic_type = 'order_'
                else:
                    continue
                pair = Pair.get_from_str(topic.replace(topic_type, ''))
                if pair.quote != self._quote_asset:
                    continue
                if topic_type == 'trade_':
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
            self._quote_asset_balance -= order.price * effective_amount

        elif order.side == Side.SHORT:
            self._add_to_position(order.pair.base, -effective_amount)
            self._quote_asset_balance += order.price * effective_amount * self.FEE_FACTOR

        else:
            raise ValueError

        publish_socket.send_multipart(
            (
                f'fill_{order.pair}'.encode(),
                msgpack.dumps(Fill(order_id, effective_amount)),
            )
        )

    def _get_next_order_id(self) -> OrderId:
        self._next_order_id += 1
        return OrderId(self._next_order_id)

    @RpcService.register
    def place_order(self, pair: Pair, side: Side, amount: Amount, price: Price) -> OrderId:
        order = Order(pair, side, amount, price)
        with self._lock:
            order_id = self._get_next_order_id()
            self._order_id_to_order_map[order_id] = order

        return order_id

    @RpcService.register
    def cancel_order(self, order_id: OrderId) -> None:
        with self._lock:
            order = self._order_id_to_order_map.get(order_id)
            if order is None or order.status in (OrderStatus.QUEUED, OrderStatus.PLACED):
                return
            assert order.price is not None
            order.status = OrderStatus.CANCELED

    @RpcService.register
    def get_order(self, order_id: OrderId) -> Order:
        return self._order_id_to_order_map[order_id]
