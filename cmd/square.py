import logging

from frog import config
from frog.square.broker import Square

if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
        filename='./logs/' + __file__.split('/')[-1].split('.')[0] + '.log',
        encoding='utf-8',
    )
    Square().run()
