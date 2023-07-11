import enum
import threading
import logging

import requests
import time

from frog.types import Pair, PriceAmountPair, Amount, Price, Side, Asset
from frog import config
from frog.utils.provider import Provider

from ._helpers import translate_asset_name


class BookWatch(Provider):
    class Topics(enum.Enum):
        best_price_amount_pair = 'best_ask_price'

    def __init__(self) -> None:
        self.book: dict[tuple(Pair, Side), list[PriceAmountPair]] = {}

    def get(self, topic: Topics, *args):
        return {
            self.Topics.best_price_amount_pair: lambda side: self.book[side][0],
        }.get(topic)(*args)

    def provide(self):
        data = requests.get(
            url='https://api.nobitex.ir/v2/orderbook/all',
            headers={
                'REFERER': 'https://nobitex.ir/',
            },).json()

        for pair in config.ALL_PAIRS:
            self.book[(pair, Side.LONG)] = []
            self.book[(pair, Side.SHORT)] = []
            price_factor = 10 if pair == Asset.RLS else 1
            for price, amount in data[translate_asset_name(pair)]['bids']:
                self.book[(pair, Side.LONG)].append(PriceAmountPair(Price(price) * price_factor, Amount(amount)))

            for price, amount in data[translate_asset_name(pair)]['asks']:
                self.book[(pair, Side.SHORT)].append(PriceAmountPair(Price(price) * price_factor, Amount(amount)))

    def run(self):
        while True:
            time.sleep(1)
            try:
                self.provide()
            except Exception as e:
                logging.error(f'failed provide{self.__class__.__name__}: {e}.')


book_watch = BookWatch()
_book_watch_thread = threading.Thread(target=book_watch.run, args=(), daemon=True)
_book_watch_thread.start()
