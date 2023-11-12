import logging
import time
import threading
import typing
import dataclasses
import decimal

import zmq

from frog import config

from frog.ordermanager.types import OrderManger, OrderId, Order, Pair, OrderStatus, Side, Fill
from frog.square.rpc import RpcService
from frog.utils import msgpack
from frog.utils.shortcuts import get_zmq_context
from frog.types import Amount, Asset, Price
from frog.tradecollector import Trade
from frog.bookwatch.types import Book

AccountId = typing.NewType('AccountId', str)


@dataclasses.dataclass
class Account:
    asset_to_balance_map: dict

    def __init__(self) -> None:
        self.asset_to_balance_map = {asset: Amount('0') for asset in Asset}


class AccountManager:
    def __init__(self) -> None:
        self._order_id_to_account_id_map: dict[OrderId, AccountId] = {}
        self._account_id_account_map: dict[AccountId, Account] = {}

    def _create_account_if_does_not_exist(self, account_id: AccountId) -> None:
        if account_id not in self._account_id_account_map:
            self._account_id_account_map[account_id] = Account()

    def add_order_for_an_account(self, order_id: OrderId, account_id: AccountId) -> None:
        self._create_account_if_does_not_exist(account_id)
        self._order_id_to_account_id_map[order_id] = account_id

    def get_order_account(self, order_id: OrderId) -> tuple[AccountId, Account]:
        account_id = self._order_id_to_account_id_map[order_id]
        return account_id, self._account_id_account_map[account_id]

    def does_order_belongs_to_account(self, order_id: OrderId, account_id: AccountId) -> bool:
        return self._order_id_to_account_id_map.get(order_id) == account_id

    def items(self) -> list[tuple[AccountId, Account]]:
        return list(self._account_id_account_map.items())

class Service(OrderManger):
    topic = b'nobifake'
    FEE_FACTOR = decimal.Decimal('0.999')

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._order_id_to_order_map: dict[OrderId, Order] = {}
        self._next_order_id = 0
        self._pair_to_orderbook_snapshot_map: dict[Pair, Book] = {}
        self._account_manager = AccountManager()
        super().__init__()

    def run_server(self) -> None:
        threading.Thread(target=self._background, args=(self._lock,), daemon=True).start()
        threading.Thread(target=self._reporter, args=(self._lock,), daemon=True).start()
        return super().run_server()

    def _fill_collector_process(self) -> None:
        return None

    def _log_account_balances(self, account_id: AccountId, account: Account):
        log_message = f'acc:{account_id},'
        for asset, balance in account.asset_to_balance_map.items():
            log_message += f'{asset}:{balance},'
        logging.info(log_message)

    def _reporter(self, lock: threading.Lock):

        while True:
            try:
                for account_id, account in self._account_manager.items():
                    with lock:
                        self._log_account_balances(account_id, account)

                for pair, book in self._pair_to_orderbook_snapshot_map.items():
                    log_message = f'piar:{pair}\t'
                    log_message += f'best bid: {book.bids[0].price}\t'
                    log_message += f'best ask: {book.asks[0].price}'
                    logging.info(log_message)

            except:
                logging.exception('Exception in Reporter')

            time.sleep(10)

    def _background(self, lock: threading.Lock):
        subscribe_socket: zmq.Socket = get_zmq_context().socket(zmq.SUB)
        subscribe_socket.subscribe('order_')
        subscribe_socket.subscribe('trade_')
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
                    raise ValueError
                pair = Pair.get_from_str(topic.replace(topic_type, ''))
                if topic_type == 'trade_':
                    with lock:
                        self._update_orders(publish_socket, msgpack.loads(data[1]))
                else:  # topic_type == 'order'
                    self._pair_to_orderbook_snapshot_map[pair] = msgpack.loads(data[1])

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
        account_id, account = self._account_manager.get_order_account(order_id)

        if order.side == Side.LONG:
            account.asset_to_balance_map[order.pair.base] += effective_amount * self.FEE_FACTOR
            account.asset_to_balance_map[order.pair.quote] -= Amount(
                (order.price * effective_amount).as_decimal(),
            )

        elif order.side == Side.SHORT:
            account.asset_to_balance_map[order.pair.base] -= effective_amount
            account.asset_to_balance_map[order.pair.quote] += Amount(
                (order.price * effective_amount * self.FEE_FACTOR).as_decimal()
            )

        else:
            raise ValueError

        publish_socket.send_multipart(
            (
                f'fill_{account_id}'.encode(),
                msgpack.dumps(Fill(order_id, effective_amount)),
            )
        )

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
