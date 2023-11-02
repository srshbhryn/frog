import logging
import time

import zmq

from frog import config
from frog.utils import msgpack

from ._client import fetch_books


def main() -> None:
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XSUB_PORT}')
    while True:
        time.sleep(1)
        try:
            for pair, book in fetch_books():
                socket.send_multipart(
                    [
                        f'order_{pair}'.encode(),
                        msgpack.dumps(book),
                    ]
                )
        except:
            logging.exception('Error in bookwatch main loop.')
