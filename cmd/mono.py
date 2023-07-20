import time
from threading import Thread

from frog import config

config.ORDERBOOK_URI = 'inproc://ORDERBOOK'
config.PRICESERVICE_URI = 'inproc://PRICESERVICE'
config.TRADECOLLECTOR_URI = 'inproc://TRADECOLLECTOR'


from cmd.orderbook import main as orderbook_main
from cmd.tradecollector import main as tradecollector_main
from cmd.tradestore import sotre_main, service_main




def main():
    for target in (
        orderbook_main,
        tradecollector_main,
        sotre_main,
        service_main,
    ):
        Thread(target=target, args=(), daemon=True).start()

    while True:
        time.sleep(1)
        pass


if  __name__ == '__main__':
    main()
