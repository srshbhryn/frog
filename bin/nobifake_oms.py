import logging

from frog import config
from frog.ordermanager.nobifake import rpc

if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    rpc.FakeOms().run_server()
