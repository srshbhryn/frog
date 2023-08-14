import asyncio
import logging

from frog import config
from frog.tradecollector import NobitexTradeCollector


def main():
    asyncio.run(NobitexTradeCollector().run())


if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    main()
