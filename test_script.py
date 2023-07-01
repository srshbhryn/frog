import logging

import os



from frog.trader import Trader


logging.basicConfig(
    format='%(module)s %(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S'
)


t = Trader(os.getenv('NOBITEX_AUTH_TOKEN'))
t.open_long('btc-rls', '1111', '10000')