import time
import dataclasses
import decimal
import logging
import queue
import threading
from typing import NewType, Optional

import zmq

from frog import config
from frog.square.rpc import RpcService
from frog.types import Amount, Pair, Price, Side, Asset
from frog.utils import msgpack
from frog.utils.shortcuts import get_zmq_context


OrderId = NewType('OrderId', int)


class OrderStatus(msgpack.Enum):
    QUEUED = 0
    PLACED = 1
    FILLED = 2
    CANCELED = 3  # also known as failed


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Order:
    pair: Pair
    side: Side
    amount: Amount
    price: Optional[Price] = None
    status: OrderStatus = OrderStatus.QUEUED
    filled_amount: Amount = Amount('0')


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Position:
    side: Side
    amount: Amount


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Fill:
    order_id: OrderId
    amount: Amount
    price: Price


class OrderManger(RpcService):
    FEE_FACTOR = decimal.Decimal('0.999')

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._publish_queue: queue.Queue = queue.Queue(maxsize=128)
        self._account_manager = AccountManager()
        self._order_id_to_order_map: dict[OrderId, Order] = {}

    def run_server(self) -> None:
        threading.Thread(
            target=self._fill_collector,
            args=(self._lock, self._publish_queue),
            daemon=True,
        ).start()
        threading.Thread(
            target=self._reporter,
            args=(self._lock, self._publish_queue),
            daemon=True,
        ).start()
        threading.Thread(
            target=self._publisher,
            args=(self._publish_queue,),
            daemon=True,
        ).start()
        return super().run_server()

    def _fill_collector(
        self,
        lock: threading.Lock,
        publish_queue: queue.Queue,
    ):
        raise NotImplementedError

    def update_orders(
        self,
        lock: threading.Lock,
        publish_queue: queue.Queue,
        fill: Fill,
    ) -> Optional[Order]:
        order_id = fill.order_id
        if not order_id in self._order_id_to_order_map:
            return None

        with lock:
            order = self._order_id_to_order_map[order_id]
            effective_amount = min(fill.amount, order.amount - order.filled_amount)
            order.filled_amount += effective_amount
            if order.filled_amount == order.amount:
                order.status = OrderStatus.FILLED
            account_id, account = self._account_manager.get_order_account(order_id)

            if order.side == Side.LONG:
                account.asset_to_balance_map[order.pair.base] += effective_amount * self.FEE_FACTOR
                account.asset_to_balance_map[order.pair.quote] -= Amount(
                    (fill.price * effective_amount).as_decimal(),
                )

            elif order.side == Side.SHORT:
                account.asset_to_balance_map[order.pair.base] -= effective_amount
                account.asset_to_balance_map[order.pair.quote] += Amount(
                    (fill.price * effective_amount * self.FEE_FACTOR).as_decimal()
                )

        publish_queue.put(
            (
                f'fill_{account_id}'.encode(),
                msgpack.dumps(fill),
            )
        )
        return order

    def _reporter(self, lock: threading.Lock, publish_queue: queue.Queue):
        oms_name = b'oms_account_' + self.topic
        while True:
            try:
                for _, account in self._account_manager.items():
                    with lock:
                        data = msgpack.dumps(account)
                    publish_queue.put((oms_name, data))
            except:
                logging.exception('Exception in Reporter')
            time.sleep(10)

    def _publisher(self, publish_queue: queue.Queue) -> None:
        publish_socket: zmq.Socket = get_zmq_context().socket(zmq.PUB)
        publish_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XSUB_PORT}')
        while True:
            publish_socket.send_multipart(publish_queue.get())

    @RpcService.register
    def place_order(self, pair: Pair, side: Side, amount: Amount, price: Price) -> OrderId:
        raise NotImplementedError

    @RpcService.register
    def cancel_order(self, order_id: OrderId) -> None:
        raise NotImplementedError

    @RpcService.register
    def get_order(self, order_id: OrderId) -> Order:
        raise NotImplementedError


AccountId = NewType('AccountId', str)


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Account:
    account_id: AccountId
    asset_to_balance_map: dict[Asset, Amount]

    def __init__(
        self,
        account_id: AccountId,
        asset_to_balance_map: Optional[dict[Asset, Amount]] = None,
    ) -> None:
        self.account_id = account_id
        if asset_to_balance_map is None:
            asset_to_balance_map = {asset: Amount('0') for asset in Asset}

        self.asset_to_balance_map = asset_to_balance_map


class AccountManager:
    def __init__(self) -> None:
        self._order_id_to_account_id_map: dict[OrderId, AccountId] = {}
        self._account_id_account_map: dict[AccountId, Account] = {}

    def _create_account_if_does_not_exist(self, account_id: AccountId) -> None:
        if account_id not in self._account_id_account_map:
            self._account_id_account_map[account_id] = Account(account_id)

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
