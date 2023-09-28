import logging
import multiprocessing

from frog import config
from frog.tradestore import rpc, store_main

if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    service = rpc.Service()
    multiprocessing.Process(target=service.run_server, args=(), daemon=True).start()
    store_main()
