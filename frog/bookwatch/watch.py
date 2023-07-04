from multiprocessing import Queue
from decimal import Decimal

from ..types import OrderBook
from ..state import State

from .fetch import fetch_books


def extract_best_prices(book):
    def extract_best_price(half_book):
        required_value = State.order_value
        for price, amount in half_book:
            price = Decimal(price)
            amount = Decimal(amount)
            value = price * amount
            if value > required_value:
                return price
        return None
    return extract_best_price(book['asks'], book['bids'])


def main(queue: Queue):
    while True:
        short_asset_book, long_asset_book = fetch_books()
        short_ask_price, short_bid_price = extract_best_prices(short_asset_book)
        long_ask_price, long_bid_price = extract_best_prices(long_asset_book)
        queue.put(OrderBook(
            short_ask_price=short_ask_price,
            short_bid_price=short_bid_price,
            long_ask_price=long_ask_price,
            long_bid_price=long_bid_price,
        ))
