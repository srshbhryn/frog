import logging

import requests

from frog import config
from frog.types import Asset, Pair, PriceAmountPair, Side

from ._helpers import translate_asset_name


class BookWatch:
    def __init__(self) -> None:
        self.book: dict[tuple[Pair, Side], list[PriceAmountPair]] = {}

    def provide(self):
        try:
            response = requests.get(
                url='https://api.nobitex.ir/v2/orderbook/all',
                headers={
                    'REFERER': 'https://nobitex.ir/',
                },
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            logging.exception('Error in BookWatch')

        for pair in config.ALL_PAIRS:
            self.book[pair, Side.LONG] = []
            self.book[pair, Side.SHORT] = []
            price_factor = 10 if pair == Asset.RLS else 1
            for price, amount in data[translate_asset_name(pair)]['bids']:
                self.book[(str(pair), str(Side.LONG))].append(
                    PriceAmountPair(price * price_factor, amount),
                )

            for price, amount in data[translate_asset_name(pair)]['asks']:
                self.book[pair, Side.SHORT].append(
                    PriceAmountPair(price * price_factor, amount),
                )
