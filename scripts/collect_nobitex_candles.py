import datetime
import logging
import time

import requests

from frog.types import Asset, Pair

from tadpoles.timescaledb import db
from tadpoles.prices.models import Candle


BACK_OFF_PERIOD = 60


def collect_nobitex_candles(
    base_asset: Asset,
    quote_asset: Asset,
    from_date: datetime.date,
    to_date: datetime.date,
):
    symbol = str(Pair(base_asset, quote_asset)).replace('rls', 'irt')
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
                f'&resolution=1'
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
                    resolution=datetime.timedelta(minutes=1),
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
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    from_date = datetime.date.fromisoformat('2021-01-01')
    to_date = datetime.date.fromisoformat('2023-11-15')
    for base_asset, quote_asset in [
        (Asset.BTC, Asset.RLS),
        (Asset.BTC, Asset.USDT),
        (Asset.ETH, Asset.RLS),
        (Asset.ETH, Asset.USDT),
        (Asset.DOGE, Asset.RLS),
        (Asset.DOGE, Asset.USDT),
        (Asset.SHIB, Asset.RLS),
        (Asset.SHIB, Asset.USDT),
        (Asset.USDT, Asset.RLS),
    ]:
        logging.info(
            'fetching %s-%s prices from %s to %s...',
            base_asset,
            quote_asset,
            from_date,
            to_date,
        )
        collect_nobitex_candles(
            base_asset,
            quote_asset,
            from_date,
            to_date,
        )
