import logging
import time
from multiprocessing import Lock
from copy import deepcopy


def get_nobitex_candle_symbol(symbol):
    return {
        'btc-rls': 'BTCIRT',
        'eth-rls': 'ETHIRT',
    }.get(symbol)


def retry_on_failure(func):
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(f'error in {func.__name__}: {e}. retrying after 1 second')
                time.sleep(1)

    return wrapper


class Store:
    def __init__(self) -> None:
        self.lock = Lock()
        self.value = None

    def get(self):
        self.lock.acquire()
        value = deepcopy(self.value)
        self.lock.release()
        return value

    def set(self, value):
        self.lock.acquire()
        self.value = deepcopy(value)
        self.lock.release()
