import logging

import requests

from frog import config

from frog.types import Asset, Price, Amount

from .types import Entry, Book
from ._helpers import translate_asset_name


def fetch_books():
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
    pairs = []
    books = []
    for pair in config.ALL_PAIRS:
        book = Book([], [])
        price_factor = 10 if pair == Asset.RLS else 1
        if not translate_asset_name(pair) in data:
            continue
        for price, amount in data[translate_asset_name(pair)]['bids']:
            book.asks.append(
                Entry(Price(float(price) * price_factor), Amount(float(amount))),
            )

        for price, amount in data[translate_asset_name(pair)]['asks']:
            book.bids.append(
                Entry(Price(float(price) * price_factor), Amount(float(amount))),
            )
        pairs.append(pair)
        books.append(book)
    return zip(pairs, books)
