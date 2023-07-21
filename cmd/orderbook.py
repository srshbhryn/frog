import logging
import time
import json

import zmq

from frog.bookwatch import BookWatch
from frog import config


def main():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(config.ORDERBOOK_BIND_URI)
    book_watch = BookWatch()
    while True:
        time.sleep(1)
        try:
            book_watch.provide()
            for (pair, side), book in book_watch.book.items():
                socket.send_multipart([
                    f'{pair}_{side}'.encode(),
                    json.dumps(book).encode(),
                ])
        except Exception as e:
            logging.error(f'failed provide {book_watch.__class__.__name__}: {e}.', exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    main()
