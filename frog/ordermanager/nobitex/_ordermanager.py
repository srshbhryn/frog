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
        self._client = NobitexClient(config.NOBITEX_TOKEN, 'frog1.1')
        self._orders: dict[OrderId, Order] = {}
        self._mutex = threading.Lock()
        super().__init__()

    def _fill_collector_process(self) -> None:
        while True:
            time.sleep(5)
            try:
                try:
                    min_oi = min(self._orders.keys())
                except Exception:
                    min_oi = OrderId(0)

                orders = self._client.request(
                    typ=self._client.Type.PRIVATE,
                    method=self._client.Method.GET,
                    url=f'/market/orders/list?status=all&details=2&fromId={min_oi}',
                )['orders']
            except:
                logging.exception('Error in fetching "/market/orders/list"')
                continue
            with self._mutex:
                for order in orders:
                    oid = order['id']
                    if oid not in self._orders:
                        continue

                    if self._orders[oid].status in (
                        OrderStatus.FILLED,
                        OrderStatus.CANCELED,
                    ):
                        continue
                    self._orders[oid].filled_amount = Amount(
                        order['matchedAmount'],
                    )
                    if order['status'] == 'Done':
                        self._orders[oid].status = OrderStatus.FILLED
                    if order['status'] == 'Canceled':
                        self._orders[oid].status = OrderStatus.CANCELED


    @RpcService.register
    def place_order(self, order: Order) -> OrderId:
        data = {
            'type': 'buy' if order.side == Side.LONG else 'sell',
            'srcCurrency': str(order.pair.base),
            'dstCurrency': str(order.pair.quote),
            'amount': str(order.amount),
            'leverage': config.NOBITEX_LEVERAGE,
        }
        if order.price:
            data['price'] = str(order.price)
        else:
            data['execution'] = 'market'

        with self._mutex:
            try:
                placed_order = self._client.request(
                    typ=self._client.Type.PRIVATE,
                    method=self._client.Method.POST,
                    url='/margin/orders/add',
                    data=data,
                )['order']
                self._orders[placed_order['id']] = order
                return placed_order['id']
            except:
                logging.exception('Error in fetching "/margin/orders/list"')
                raise

    @RpcService.register
    def cancel_order(self, order_id: OrderId) -> None:
        self._client.request(
            typ=self._client.Type.PRIVATE,
            method=self._client.Method.POST,
            url='/market/orders/update-status',
            data={
                'order': order_id,
                'status': 'canceled',
            },
        )

    @RpcService.register
    def get_order(self, order_id: OrderId) -> Order:
        with self._mutex:
            return self._orders[order_id]
