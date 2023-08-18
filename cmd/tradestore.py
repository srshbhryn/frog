import asyncio
import logging
import multiprocessing

from frog import config
from frog.tradestore import NobitexTradeCollector, rpc, store_main

if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    multiprocessing.Process(target=rpc.Service(), args=(), daemon=True).start()
    multiprocessing.Process(target=store_main(), args=(), daemon=True).start()
    asyncio.run(NobitexTradeCollector().run())
