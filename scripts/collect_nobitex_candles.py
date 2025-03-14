import datetime
import logging
import time
import sys

import requests

from frog.types import Asset, Pair

from tadpoles.timescaledb import get_db
from tadpoles.prices.models import Candle


db = get_db()

BACK_OFF_PERIOD = 60


def collect_nobitex_candles(
    base_asset: Asset,
    quote_asset: Asset,
    from_date: datetime.date,
    to_date: datetime.date,
    resolution: datetime.timedelta,
):
    symbol = str(Pair(base_asset, quote_asset)).replace('rls', 'irt')
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
    to_datetime = datetime.datetime.combine(
        to_date,
        datetime.time.max,
        datetime.timezone(datetime.timedelta(hours=0)),
    )
    to_timestamp = int(to_datetime.timestamp())
    from_datetime = datetime.datetime.combine(
        from_date,
        datetime.time.min,
        datetime.timezone(datetime.timedelta(hours=0)),
    )

    from_timestamp = int(from_datetime.timestamp())
    added_timestamps = set()
    max_fetched_timestamp = -999999999999999999
    min_fetched_timestamp = 999999999999999999
    page = 1
    while max_fetched_timestamp < to_timestamp or min_fetched_timestamp > from_timestamp:
        try:
            url = (
                'https://api.nobitex.ir/market/udf/history'
                f'?symbol={symbol}'
                f'&resolution={resolution_payload}'
                f'&to={to_timestamp}'
                f'&from={from_timestamp}'
                f'&page={page}'
            )
            logging.info('fetching %s', url)
            response = requests.get(
                url=url,
                headers={
                    'REFERER': 'https://nobitex.ir/',
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except:
            logging.exception('request exception: sleeping for %d seconds...', BACK_OFF_PERIOD)
            time.sleep(BACK_OFF_PERIOD)
        if not data['s'] == 'ok':
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
            if int(t) in added_timestamps:
                continue
            added_timestamps.add(int(t))
            candles.append(
                Candle(
                    base_asset=str(base_asset),
                    quote_asset=str(quote_asset),
                    exchange='nobitex',
                    resolution=resolution,
                    timestamp=datetime.datetime.fromtimestamp(t, tz=datetime.timezone(datetime.timedelta())),
                    min_price=l,
                    max_price=h,
                    open_price=o,
                    close_price=c,
                    volume=v,
                )
            )
        db.add_all(candles)
        max_fetched_timestamp = max(added_timestamps)
        min_fetched_timestamp = min(added_timestamps)
        page += 1
        db.commit()

    db.query(Candle).filter(Candle.timestamp < from_datetime).delete()
    db.query(Candle).filter(Candle.timestamp > to_datetime).delete()
    db.commit()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        logging.error('Invalid number of arguments.')
    try:
        from_date_arg = sys.argv[1]
        from_date = datetime.date.fromisoformat(from_date_arg)
    except:
        logging.error('invalid from date arg: %s', from_date_arg)
        sys.exit(1)

    try:
        to_date_arg = sys.argv[2]
        to_date = datetime.date.fromisoformat(to_date_arg)
    except:
        logging.error('invalid to date arg: %s', to_date_arg)
        sys.exit(1)

    try:
        resolution = None
        resolution_arg = sys.argv[3]
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
        logging.error('invalid to date arg: %s', to_date_arg)
        sys.exit(1)

    symbols = []
    for symbol_arg in sys.argv[4:]:
        try:
            base_arg, quote_arg = symbol_arg.split('-')
            base_asset = Asset(base_arg)
            quote_asset = Asset(quote_arg)
        except:
            logging.error('invalid symbol arg: %s', symbol_arg)
            sys.exit(1)

        symbols.append((base_asset, quote_asset))

    for base_asset, quote_asset in symbols:
        collect_nobitex_candles(
            base_asset,
            quote_asset,
            from_date,
            to_date,
            resolution,
        )
