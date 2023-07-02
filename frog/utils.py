import logging
import time


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
