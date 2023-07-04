from multiprocessing import Queue
import logging

from ..utils import Store
from ..types import Interpolation, OrderBook
from ..state import State, Ticker, Position
from ..config import Config

from .core import Core



def get_residual(long_price, short_price, interpolation: Interpolation):
    return long_price / interpolation.long_price_zero - interpolation.alpha - interpolation.beta * (
        short_price / interpolation.short_price_zero
    )


def main(order_book_queue: Queue, interpolation_store: Store):
    while True:
        orderbook: OrderBook = order_book_queue.get()
        interpolation = interpolation_store.get()
        shorting_residual = get_residual(
            orderbook.long_bid_price,
            orderbook.short_ask_price,
            interpolation,
        )
        longing_residual = get_residual(
            orderbook.long_ask_price,
            orderbook.short_bid_price,
            interpolation,
        )

        if State.position == Position.CLOSE and longing_residual < -Config.alpha_open:
            Core.open_long(orderbook.long_ask_price, orderbook.short_bid_price)

        elif State.position == Position.CLOSE and shorting_residual > Config.alpha_open:
            Core.open_short(orderbook.long_bid_price, orderbook.short_ask_price)

        elif State.position == Position.SHORT and longing_residual < Config.alpha_close:
            Core.close_short(orderbook.long_ask_price, orderbook.short_bid_price)

        elif State.position == Position.LONG and shorting_residual > -Config.alpha_close:
            Core.close_long(orderbook.long_bid_price, orderbook.short_ask_price)
