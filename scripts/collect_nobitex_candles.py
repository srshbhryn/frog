import datetime
import logging
import sys
import time

import requests

from frog.types import Asset, Pair

from tadpoles.prices.db import Candle, db


TIMEOUT_BACK_OFF_PERIOD = 60


def collect_nobitex_candles(
    base_asset: Asset,
    quote_asset: Asset,
    from_date: datetime.date,  # inclusive
    to_date: datetime.date,  # exclusive
):
    symbol = str(Pair(base_asset, quote_asset)).replace('rls', 'irt')
    to_timestamp = int(
        datetime.datetime.combine(
            to_date,
            datetime.time.min,
            datetime.timezone(datetime.timedelta(hours=0)),
        ).timestamp()
    )
    from_timestamp = int(
        datetime.datetime.combine(
            from_date,
            datetime.time.min,
            datetime.timezone(datetime.timedelta(hours=0)),
        ).timestamp()
    )

    last_fetched_timestamp = 0
    page = 1
    while last_fetched_timestamp != from_timestamp:
        try:
            response = requests.get(
                url=(
                    'https://api.nobitex.ir/market/udf/history'
                    f'?symbol={symbol}'
                    f'&resolution=1'
                    f'&to={to_timestamp}'
                    f'&from={from_timestamp}'
                    f'&page={page}'
                ),
                headers={
                    'REFERER': 'https://nobitex.ir/',
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except requests.Timeout:
            logging.info('requets timeout: sleeping for %d seconds...', TIMEOUT_BACK_OFF_PERIOD)
            time.sleep(TIMEOUT_BACK_OFF_PERIOD)
        if not data['s'] == 'ok':
            logging.error('bad response: "%s".', response.text)
            sys.exit(1)
        db.add_all(
            [
                Candle(
                    base_asset=str(base_asset),
                    quote_asset=str(quote_asset),
                    exchange='nobitex',
                    resolution=1,
                    timestamp=t,
                    min_price=l,
                    max_price=h,
                    open_price=o,
                    close_price=c,
                    volume=v,
                )
                for t, o, c, h, l, v in zip(
                    data['t'],
                    data['o'],
                    data['c'],
                    data['h'],
                    data['l'],
                    data['v'],
                )
            ]
        )
        db.commit()
        last_fetched_timestamp = data['t'][0]
        page += 1


if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    base_asset = Asset(sys.argv[1])
    quote_asset = Asset(sys.argv[2])
    from_date = datetime.date.fromisoformat(sys.argv[3])
    to_date = datetime.date.fromisoformat(sys.argv[4])
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
