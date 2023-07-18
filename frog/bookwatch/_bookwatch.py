
import requests

from frog.types import Pair, PriceAmountPair, Side, Asset
from frog import config
from frog.utils.provider import Provider

from ._helpers import translate_asset_name


class BookWatch(Provider):
    def __init__(self) -> None:
        self.book: dict[tuple(Pair, Side), list[PriceAmountPair]] = {}

    def provide(self):
        data = requests.get(
            url='https://api.nobitex.ir/v2/orderbook/all',
            headers={
                'REFERER': 'https://nobitex.ir/',
            },).json()

        for pair in config.ALL_PAIRS:
            self.book[(str(pair), str(Side.LONG))] = []
            self.book[(str(pair), str(Side.SHORT))] = []
            price_factor = 10 if pair == Asset.RLS else 1
            for price, amount in data[translate_asset_name(pair)]['bids']:
                self.book[(str(pair), str(Side.LONG))].append((price * price_factor, amount))

            for price, amount in data[translate_asset_name(pair)]['asks']:
                self.book[(str(pair), str(Side.SHORT))].append((price * price_factor, amount))
