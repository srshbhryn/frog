import logging
import threading
import time

from frog import config
from frog.ordermanager.types import (
    Amount,
    Order,
    OrderId,
    OrderManger,
    OrderStatus,
    Side,
)
from frog.square.rpc import RpcService

from ._client import Client as NobitexClient


class Service(OrderManger):
    topic = b'nobitex'

    def __init__(self) -> None:
        self._client = NobitexClient(config.NOBITEX_TOKEN, 'frog1.0')
        self._orders: dict[OrderId, Order] = {}
        self._mutex = threading.Lock()

    def _fill_collector_process(self) -> None:
        while True:
            time.sleep(5)
            try:
                try:
                    min_oi = min(self._orders.keys())
                except Exception:
                    min_oi = 0

                orders = self._client.request(
                    typ=self._client.Type.private,
                    method=self._client.Method.get,
                    url=f'/market/orders/list?status=all&details=2&fromId={min_oi}',
                )['orders']
            except:
                logging.exception('Error in fetching "/market/orders/list"')
                continue
            self._mutex.acquire()
            try:
                for order in orders:
                    oid = order['id']
                    if oid not in self._orders:
                        continue

                    if self._orders[oid].status in (
                        OrderStatus.filled,
                        OrderStatus.canceled,
                    ):
                        continue
                    self._orders[oid].filled_amount = Amount(
                        order['matchedAmount'],
                    )
                    if order['status'] == 'Done':
                        self._orders[oid].status = OrderStatus.filled
                    if order['status'] == 'Canceled':
                        self._orders[oid].status = OrderStatus.canceled

            finally:
                self._mutex.release()

    @RpcService.register
    def place_order(self, order: Order) -> int:
        data = {
            'type': 'buy' if order.side == Side.LONG else 'sell',
            'srcCurrency': str(order.pair.base),
            'dstCurrency': str(order.pair.quote),
            'amount': str(order.amount),
        }
        if order.price:
            data['price'] = str(order.price)
        else:
            data['execution'] = 'market'

        self._mutex.acquire()
        try:
            placed_order = self._client.request(
                typ=self._client.Type.private,
                method=self._client.Method.post,
                url='/market/orders/add',
                data=data,
            )['order']
            self._orders[placed_order['id']] = order
            return placed_order['id']
        except:
            logging.exception('Error in fetching "/market/orders/list"')
            raise
        finally:
            self._mutex.release()

    @RpcService.register
    def cancel_order(self, order_id: OrderId) -> None:
        self._client.request(
            typ=self._client.Type.private,
            method=self._client.Method.post,
            url='/market/orders/update-status',
            data={
                'order': order_id,
                'status': 'canceled',
            },
        )

    @RpcService.register
    def get_order(self, order_id: OrderId) -> Order:
        self._mutex.acquire()
        try:
            return self._orders[order_id]
        finally:
            self._mutex.release()
