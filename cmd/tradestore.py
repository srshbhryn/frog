import logging
import multiprocessing

from frog import config
from frog.tradestore import rpc, store_main

if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
        filename='./' + __file__.split('/')[-1].split('.')[0] + '.log',
        encoding='utf-8',
    )

    multiprocessing.Process(target=rpc.Service, args=(), daemon=True).start()
    store_main()
