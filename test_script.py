import logging
import time
import os



from frog.trader import Trader


logging.basicConfig(
    format='%(module)s %(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S'
)


t = Trader(os.getenv('NOBITEX_AUTH_TOKEN'))
# t._get_position_id_and_liability('btc-rls')
# t.open_short('btc-rls', '.0001', '15235245000')
time.sleep(3)
t.close_all_short('btc-rls',  '16236245000')

