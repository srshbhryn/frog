from multiprocessing import Queue
import time
import logging
import decimal

# from ..utils import Store
from ..types import Interpolation, OrderBook
from ..state import State, Ticker, Position
from ..config import Config

from .core import Core



def get_residual(long_price, short_price, interpolation: Interpolation):
    return float(long_price) / interpolation.long_price_normalizer - interpolation.reg.predict([[1, float(short_price) / interpolation.short_price_normalizer]])[0]


def main(order_book_queue: Queue, interpolation_queue: Queue):
    while True:
        orderbook: OrderBook = order_book_queue.get()
        logging.info(orderbook)
        interpolation: IndentationError = interpolation_queue.get()
        interpolation_queue.put(interpolation)
        if interpolation is None:
            logging.info('interpolation is not available')
            time.sleep(1)
            continue
        logging.info(interpolation)
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
        logging.info(f'shorting_residual, {shorting_residual}')
        logging.info(f'longing_residual, {longing_residual}')
        if State.position == Position.CLOSE and longing_residual < -Config.alpha_open:
            Core.open_long(orderbook.long_ask_price, orderbook.short_bid_price)

        elif State.position == Position.CLOSE and shorting_residual > Config.alpha_open:
            Core.open_short(orderbook.long_bid_price, orderbook.short_ask_price)

        elif State.position == Position.SHORT and longing_residual < Config.alpha_close:
            Core.close_short(orderbook.long_ask_price, orderbook.short_bid_price)

        elif State.position == Position.LONG and shorting_residual > -Config.alpha_close:
            Core.close_long(orderbook.long_bid_price, orderbook.short_ask_price)
