import requests
import time

from .state import State
from .config import Config
from .utils import get_nobitex_candle_symbol, retry_on_failure

@retry_on_failure
def get_prices(symbol: str) -> list[float]:
    ticker = int(State.ticker)
    timestamp_to_open_map = _fetch_prices(
        symbol=get_nobitex_candle_symbol(symbol),
        from_timestamp=int(ticker) - 60 * (Config.residual_length + 5),
        to_timestamp=int(ticker),
        resolution='1',
    )
    if not int(ticker) in timestamp_to_open_map:
        time.sleep(1)
        return get_prices(symbol)
    f = 10 if symbol[-3:] == 'rls' else 1
    return [
        f * timestamp_to_open_map[ts]
        for ts in range(ticker - 60 * Config.residual_length + 60, ticker + 60, 60)
    ]


def _fetch_prices(
    symbol,
    from_timestamp,  # inclusive
    to_timestamp,  # exclusive
    resolution,
):
    timestamp_to_open_map = {}
    last_fetched_timestamp = 0
    page = 1
    while last_fetched_timestamp != from_timestamp:
        data = requests.get(url=(
        'https://api.nobitex.ir/market/udf/history'
        f'?symbol={symbol}'
        f'&resolution={resolution}'
        f'&to={to_timestamp}'
        f'&from={from_timestamp}'
        f'&page={page}'
        ), headers={
            'REFERER': 'https://nobitex.ir/',
        },).json()
        for  t, o, c, h, l, v in zip(
            data['t'],
            data['o'],
            data['c'],
            data['h'],
            data['l'],
            data['v'],
        ):
            timestamp_to_open_map[int(t) + 60] = float(c)
        last_fetched_timestamp = data['t'][0]
        page += 1

    return timestamp_to_open_map
