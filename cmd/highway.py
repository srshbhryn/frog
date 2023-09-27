import logging

import zmq

from frog import config


def main() -> None:

    context = zmq.Context()

    frontend = context.socket(zmq.XPUB)
    frontend.bind(f'tcp://*:{config.HIGHWAY_XPUB_PORT}')
    frontend.bind(f'tcp://{config._HIGHWAY_HOST}:{config._HIGHWAY_XPUB_PORT}')

    backend = context.socket(zmq.XSUB)
    backend.bind(f'tcp://*:{config.HIGHWAY_XSUB_PORT}')
    backend.bind(f'tcp://{config._HIGHWAY_HOST}:{config._HIGHWAY_XSUB_PORT}')

    zmq.proxy(frontend, backend)

    # We never get here…
    frontend.close()
    backend.close()
    context.term()


if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        # level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    main()
