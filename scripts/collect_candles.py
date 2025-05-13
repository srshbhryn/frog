import datetime
import logging
import time
import sys
import uuid

import requests

from frog.types import Asset, Pair
from tadpoles.types import Exchange

from tadpoles.timescaledb import get_db
from tadpoles.prices.models import Candle


def get_candle_api(exchange: Exchange):
    return {
        Exchange.WALLEX: 'https://api.wallex.ir/v1/udf/history',
        Exchange.OMPFINEX: 'https://api.ompfinex.com/v2/udf/real/history',
    }[exchange]

def translate_udf_symbol(symbol: str, exchange: Exchange):
    if exchange == Exchange.WALLEX:
        return symbol.replace('irt', 'tmn')
    return symbol

def datetime_range(
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    delta: datetime.timedelta | None = datetime.timedelta(days=1),
) -> list[datetime.datetime]:
    dtr = []
    current_datetime = start_datetime
    while current_datetime < end_datetime:
        print(current_datetime, end_datetime)
        dtr.append(current_datetime)
        current_datetime += delta
    return dtr

db = get_db()

BACK_OFF_PERIOD = 60


def collect_candles(
    exchange: Exchange,
    base_asset: Asset,
    quote_asset: Asset,
    from_datetime: datetime.datetime,
    to_datetime: datetime.datetime,
    resolution: datetime.timedelta,
):
    symbol = translate_udf_symbol(
        str(Pair(base_asset, quote_asset)).replace('rls', 'irt'),
        exchange,
    )
    resolution_payload = {
        datetime.timedelta(minutes=1): '1',
        datetime.timedelta(minutes=5): '5',
        datetime.timedelta(minutes=15): '15',
        datetime.timedelta(minutes=30): '30',
        datetime.timedelta(hours=1): '60',
        datetime.timedelta(hours=3): '180',
        datetime.timedelta(hours=4): '240',
        datetime.timedelta(hours=6): '360',
        datetime.timedelta(hours=12): '720',
        datetime.timedelta(days=1): 'D',
        datetime.timedelta(days=2): '2D',
        datetime.timedelta(days=3): '3D',
    }.get(resolution)
    if resolution_payload is None:
        raise ValueError('invalid resolution')
    to_timestamp = int(to_datetime.timestamp())
    from_timestamp = int(from_datetime.timestamp())
    added_timestamps = set()
    while True:
        try:
            log_id = uuid.uuid4().hex[:8]
            url = (
                f'{get_candle_api(exchange)}'
                f'?symbol={symbol.upper()}'
                f'&resolution={resolution_payload}'
                f'&from={from_timestamp}'
                f'&to={to_timestamp}'
                # '&countback=100'
            )
            logging.info('log_id: %s\tfetching %s', log_id, url)
            response = requests.get(
                url=url,
                timeout=10,
                headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
            )
            response.raise_for_status()
            data = response.json()
        except:
            logging.exception('log_id: %s\trequest exception: sleeping for %d seconds...', log_id, BACK_OFF_PERIOD)
            time.sleep(BACK_OFF_PERIOD)
            continue
        if not data['s'] == 'ok':
            logging.info('log_id: %s\t status: %s', log_id, data['s'])
            break
        candles = []
        for t, o, c, h, l, v in set(
            zip(
                data['t'],
                data['o'],
                data['c'],
                data['h'],
                data['l'],
                data['v'],
            )
        ):
            ts = int(t)
            if ts >= to_timestamp or ts < from_timestamp:
                continue
            added_timestamps.add(ts)
            candles.append(
                Candle(
                    base_asset=str(base_asset),
                    quote_asset=str(quote_asset),
                    exchange=exchange.value,
                    resolution=resolution,
                    timestamp=datetime.datetime.fromtimestamp(ts, tz=datetime.timezone(datetime.timedelta())),
                    min_price=l,
                    max_price=h,
                    open_price=o,
                    close_price=c,
                    volume=v,
                )
            )
        db.add_all(candles)
        db.commit()
        break

if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    if len(sys.argv) < 5:
        logging.error('Invalid number of arguments.')
    try:
        exchange = Exchange(sys.argv[1])
    except:
        logging.error('Invalid exchange arg.')
    try:
        from_date_arg = sys.argv[2]
        from_date = datetime.date.fromisoformat(from_date_arg)
    except:
        logging.error('invalid from date arg: %s', from_date_arg)
        sys.exit(1)

    try:
        to_date_arg = sys.argv[3]
        to_date = datetime.date.fromisoformat(to_date_arg)
    except:
        logging.error('invalid to date arg: %s', to_date_arg)
        sys.exit(1)

    try:
        resolution = None
        resolution_arg = sys.argv[4]
        for unit, unit_resolution in [
            ('d', datetime.timedelta(days=1)),
            ('h', datetime.timedelta(hours=1)),
            ('m', datetime.timedelta(minutes=1)),
            ('s', datetime.timedelta(seconds=1)),
        ]:
            if resolution_arg[-1] == unit:
                resolution = int(resolution_arg[:-1]) * unit_resolution
                break
        assert resolution is not None
    except:
        logging.error('invalid resolution: %s', resolution_arg)
        sys.exit(1)

    symbols = []
    for symbol_arg in sys.argv[5:]:
        try:
            base_arg, quote_arg = symbol_arg.split('-')
            base_asset = Asset(base_arg)
            quote_asset = Asset(quote_arg)
        except:
            logging.error('invalid symbol arg: %s', symbol_arg)
            sys.exit(1)

        symbols.append((base_asset, quote_asset))

    delta = datetime.timedelta(hours=6)
    for base_asset, quote_asset in symbols:
        for dt in datetime_range(
            datetime.datetime.combine(from_date, datetime.time.min),
            datetime.datetime.combine(to_date, datetime.time.min),
            delta,
        ):
            collect_candles(
                exchange,
                base_asset,
                quote_asset,
                dt,
                dt + delta,
                resolution,
            )
