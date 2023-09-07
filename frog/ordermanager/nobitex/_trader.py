from typing import TYPE_CHECKING

from frog.types import Amount, Asset, Pair

from ._client import Client

if TYPE_CHECKING:
    from frog.ordermanager.types import OrderStore, Position


class Trader:
    def __init__(self, token: str) -> None:
        self.token = token
        self.client = Client(token, 'frog1.0')
        self.spot_balances: dict[Asset, Amount] = {}
        self.margin_balances: dict[Asset, Amount] = {}
        self.positions: dict[Pair, Position] = {}
        self.open_orders: dict[Pair, OrderStore]

    def _init(self) -> None:
        known_currencies = ','.join(a.value for a in list(Asset))

        def _fetch_balances(tp: str, target: dict):
            self.client.request(
                self.client.Type.private,
                self.client.Method.get,
                f'/v2/wallets?type={tp}&currencies={known_currencies}',
            )

        def fetch_positions():
            pass

        def fetch_open_orders():
            pass

        _fetch_balances('spot', self.spot_balances)
        _fetch_balances('margin', self.margin_balances)
        fetch_positions()
        fetch_open_orders()
