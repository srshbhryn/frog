import logging

import os



from frog.trader import Trader


logging.basicConfig(
    format='%(module)s %(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S'
)


t = Trader(os.getenv('NOBITEX_AUTH_TOKEN'))
t.open_short('btc-rls', '.00001', '152352452300')

