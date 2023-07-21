import logging
import multiprocessing

from frog.tradestore import sotre_main, service_main
from frog import config

if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    multiprocessing.Process(target=service_main, args=(), daemon=True).start()
    sotre_main()
