import dataclasses
import threading
from typing import NewType, Optional

from frog.square.rpc import RpcService
from frog.types import Amount, Pair, Price, Side, Asset
from frog.utils import msgpack


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


class OrderManger(RpcService):

    def run_server(self) -> None:
        threading.Thread(target=self._fill_collector_process, daemon=True).start()
        super().run_server()

    def _fill_collector_process(self) -> None:
        raise NotImplementedError

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
    asset_to_balance_map: dict

    def __init__(self, account_id: AccountId) -> None:
        self.account_id = account_id
        self.asset_to_balance_map = {asset: Amount('0') for asset in Asset}


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
