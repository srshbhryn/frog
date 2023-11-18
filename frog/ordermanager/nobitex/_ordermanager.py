import logging
import queue
import threading
import time

from frog import config
from frog.types import Pair, Price, Amount, Side
from frog.ordermanager.types import (
    Fill,
    AccountId,
    Order,
    OrderId,
    OrderManger,
)
from frog.square.rpc import RpcService

from ._client import Client
from ._position_manager import PositionManger


class Service(OrderManger):
    topic = b'nobitex'

    def __init__(self) -> None:
        super().__init__()
        self._client = Client(config.NOBITEX_TOKEN, 'frog-1.5')
        self._position_manager = PositionManger(self._client)

    def _fill_collector(self, lock: threading.Lock, publish_queue: queue.Queue):
        last_fetched_fill_id = -1
        client = Client(config.NOBITEX_TOKEN, 'frog-1.5')
        while True:
            time.sleep(3)
            url = f'market/trades/list?pageSize=500&fromId={last_fetched_fill_id+1}'
            try:
                response = client.request(Client.Type.PRIVATE, Client.Method.GET, url)
                for trade in response['trades']:
                    fill = Fill(
                        OrderId(trade['orderId']),
                        Amount(trade['amount']),
                        Price(trade['price']),
                    )
                    order = self.update_orders(lock, publish_queue, fill)
                    if order is None:
                        return
                    self._position_manager.apply_close_order_fill_to_position(
                        order.pair,
                        order.side,
                        fill,
                    )
                if len(response['trades']) > 0:
                    last_fetched_fill_id = response['trades'][0]['id']

            except:
                logging.exception('Error in fetching "%s"', url)
                continue

    @RpcService.register
    def place_order(
        self,
        pair: Pair,
        side: Side,
        amount: Amount,
        price: Price,
        **kwargs,
    ) -> OrderId:
        position = self._position_manager.get_position_by_pair_side(pair, -side)
        if position is None:
            raise RpcService.Err(RpcService.Err.Code.NOT_AVAILABLE, 'no position to close')
        url = f'/positions/{position.position_id}/close'
        with self._lock:
            try:
                placed_order = self._client.request(
                    typ=self._client.Type.PRIVATE,
                    method=self._client.Method.POST,
                    url=url,
                    data={
                        'amount': str(amount),
                        'price': str(price),
                    },
                )['order']
                order = Order(
                    pair=pair,
                    side=side,
                    amount=amount,
                    price=price,
                )
                order_id = OrderId(placed_order['id'])
                self._order_id_to_order_map[order_id] = order
                self._account_manager.add_order_for_an_account(
                    order_id,
                    AccountId(kwargs['client_identity']),
                )
                return order_id
            except:
                logging.exception('Error in fetching "%s"', url)
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
        with self._lock:
            return self._order_id_to_order_map[order_id]
