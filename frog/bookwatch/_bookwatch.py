import logging

import requests

from frog import config
from frog.types import Asset, Pair, Side

from ._helpers import translate_asset_name


class BookWatch:
    def __init__(self) -> None:
        self.book: dict[tuple[Pair, Side], list[tuple(float, float)]] = {}

    def provide(self) -> None:
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
                self.book[pair, Side.LONG].append(
                    (float(price) * price_factor, float(amount)),
                )

            for price, amount in data[translate_asset_name(pair)]['asks']:
                self.book[pair, Side.SHORT].append(
                    (float(price) * price_factor, float(amount)),
                )
