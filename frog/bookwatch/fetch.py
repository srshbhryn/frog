import requests

from ..config import Config
from ..utils import get_nobitex_candle_symbol, retry_on_failure


@retry_on_failure
def fetch_books():
    data = requests.get(
        url='https://api.nobitex.ir/v2/orderbook/all',
        headers={
            'REFERER': 'https://nobitex.ir/',
        },).json()
    assert data['status'] == 'ok'
    short_asset_symbol = get_nobitex_candle_symbol(Config.short_symbol)
    long_asset_symbol = get_nobitex_candle_symbol(Config.long_symbol)
    return {
        'bids': data[short_asset_symbol]['asks'],
        'asks': data[short_asset_symbol]['bids'],
    }, {
        'bids': data[long_asset_symbol]['asks'],
        'asks': data[long_asset_symbol]['bids'],
    }
