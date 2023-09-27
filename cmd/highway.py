import logging

import zmq

from frog import config


def main() -> None:

    context = zmq.Context()

    frontend = context.socket(zmq.XPUB)
    frontend.bind(f'tcp://*:{config.HIGHWAY_XPUB_PORT}')

    backend = context.socket(zmq.XSUB)
    backend.bind(f'tcp://*:{config.HIGHWAY_XSUB_PORT}')

    zmq.proxy(frontend, backend)

    # We never get here…
    frontend.close()
    backend.close()
    context.term()


if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
        filename='./logs/' + __file__.split('/')[-1].split('.')[0] + '.log',
        encoding='utf-8',
    )
    main()
