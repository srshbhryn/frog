from typing import TYPE_CHECKING
import decimal
import logging
import time
import threading

from frog.types import Amount, Asset, Pair
from frog.utils.rpc import ZmqRpc
from frog.ordermanager.types import (
    Order,
    OrderId,
    Position,
    OrderManger as BaseOrderManager,
    OrderStatus,
)

from ._client import Client


class OrderManager(BaseOrderManager):
    def __init__(self, token: str) -> None:
        self.token = token

        self._client = Client(token, 'frog1.0')
        self._orders: dict[OrderId, Order] = {}
        self._mutex = threading.Lock()

    def _fill_collector_process(self) -> None:
        while True:
            time.sleep(5)
            try:
                orders = self._client.request(
                    typ=self._client.Type.private,
                    method=self._client.Method.get,
                    url='/market/orders/list',
                )['orders']
            except:
                logging.exception('Error in fetching "/market/orders/list"')
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
                    self._orders[oid].filled_amount = decimal.Decimal(
                        order['matchedAmount'],
                    )
                    if order['status'] == 'Done':
                        self._orders[oid].status = OrderStatus.filled
                    if order['status'] == 'Canceled':
                        self._orders[oid].status = OrderStatus.canceled

            finally:
                self._mutex.release()

    @ZmqRpc.register
    def place_order(self, order: Order) -> None:
        try:
            placed_order = self._client.request(
                typ=self._client.Type.private,
                method=self._client.Method.get,
                url='/market/orders/add',
                data={},
            )['order']
            self._orders[placed_order['id']] = order

        except:
            logging.exception('Error in fetching "/market/orders/list"')
            raise
        finally:
            self._mutex.release()

    @ZmqRpc.register
    def cancel_order(self, order_id: OrderId) -> None:
        self._client.request(
            typ=self._client.Type.private,
            method=self._client.Method.post,
            url='/market/orders/update-status',
            data={
                'id': order_id,
                'status': 'canceled',
            },
        )

    @ZmqRpc.register
    def get_order(self, order_id: OrderId) -> Order:
        self._mutex.acquire()
        try:
            return self._orders[order_id]
        finally:
            self._mutex.release()
