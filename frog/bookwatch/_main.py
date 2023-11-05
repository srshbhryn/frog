import logging
import time

import zmq

from frog import config
from frog.utils import msgpack

from ._client import fetch_books
from ._helpers import BookStore


def main() -> None:
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XSUB_PORT}')
    book_store = BookStore()
    while True:
        time.sleep(1)
        try:
            for pair, book in fetch_books():
                if not book_store.is_a_new_book(pair, book):
                    continue
                socket.send_multipart(
                    [
                        f'order_{pair}'.encode(),
                        msgpack.dumps(book),
                    ]
                )
        except:
            logging.exception('Error in bookwatch main loop.')
