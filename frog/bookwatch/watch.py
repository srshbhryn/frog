import time
from multiprocessing import Queue
from decimal import Decimal

from ..types import OrderBook
from ..config import Config

from .fetch import fetch_books


def extract_best_price(half_book, required_value):
    for price, amount in half_book:
        price = Decimal(price)
        amount = Decimal(amount)
        value = price * amount
        if value > required_value:
            return price
    return None


def main(queue: Queue):
    while True:
        short_asset_book, long_asset_book = fetch_books()
        short_ask_price = extract_best_price(short_asset_book['asks'], Config.short_order_value())
        short_bid_price = extract_best_price(short_asset_book['bids'], Config.short_order_value())
        long_ask_price = extract_best_price(long_asset_book['asks'], Config.long_order_value())
        long_bid_price = extract_best_price(long_asset_book['bids'], Config.long_order_value())
        queue.put(OrderBook(
            short_ask_price=short_ask_price,
            short_bid_price=short_bid_price,
            long_ask_price=long_ask_price,
            long_bid_price=long_bid_price,
        ))
        time.sleep(.8)

