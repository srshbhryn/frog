import json
import logging
import time

import zmq

from frog import config
from ._bookwatch import BookWatch


def main() -> None:
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XSUB_PORT}')
    book_watch = BookWatch()
    while True:
        time.sleep(1)
        try:
            book_watch.provide()
            for (pair, side), book in book_watch.book.items():
                socket.send_multipart(
                    [
                        f'order_{pair}_{side}'.encode(),
                        json.dumps(book).encode(),
                    ]
                )
        except Exception:
            logging.exception('failed provide "%s".', book_watch.__class__.__name__)
