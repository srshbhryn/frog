import json
import logging
import time

import zmq

from frog import config
from frog.bookwatch import BookWatch


def main() -> None:
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect(config.HIGHWAY_XSUB_URI)
    book_watch = BookWatch()
    while True:
        time.sleep(1)
        try:
            book_watch.provide()
            for (pair, side), book in book_watch.book.items():
                socket.send_multipart([
                    f'order_{pair}_{side}'.encode(),
                    json.dumps(book).encode(),
                ])
        except Exception:
            logging.exception('failed provide "%s".', book_watch.__class__.__name__)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
        filename='../' + __file__.split('/')[-1].split('.')[0] + '.log',
        encoding='utf-8',
    )
    main()
