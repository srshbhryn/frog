import logging
import sys
from datetime import timedelta

from sqlalchemy import func

from frog.types import Asset

from tadpoles.types import Exchange
from tadpoles.prices.models import Candle
from tadpoles.timescaledb import db


def main(
    base_asset: Asset,
    quote_asset: Asset,
    exchange: Exchange,
    resolution: timedelta,
    create_missing_data: bool,
):
    pair_filter = [
        Candle.exchange == exchange.value,
        Candle.base_asset == base_asset.value,
        Candle.quote_asset == quote_asset.value,
        Candle.resolution == resolution,
    ]
    from_timestamp, to_timestamp = (
        db.query(
            func.min(Candle.timestamp),
            func.max(Candle.timestamp),
        )
        .filter(*pair_filter)
        .first()
    )

    time_index_delta = timedelta(days=3)
    from_timestamp -= resolution
    from_timestamp -= time_index_delta

    while from_timestamp < to_timestamp:
        from_timestamp += time_index_delta
        ts_upper_bound = min(to_timestamp, from_timestamp + time_index_delta)
        existing_timestamps = list(
            db.query(Candle.timestamp)
            .filter(
                *pair_filter,
                *[
                    Candle.timestamp > from_timestamp,
                    Candle.timestamp <= ts_upper_bound,
                ],
            )
            .distinct()
        )
        number_of_excepted_timestamp = int((ts_upper_bound - from_timestamp) / resolution)

        if number_of_excepted_timestamp == len(existing_timestamps):
            continue
        for ts in [from_timestamp + (1 + i) * resolution for i in range(number_of_excepted_timestamp)]:
            if ts in existing_timestamps:
                continue
            print(f'timestamp {ts} is missing')


if __name__ == '__main__':
    (
        base_asset,
        quote_asset,
        resolution,
        *args,
    ) = sys.argv[1:]
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    main(
        Asset(base_asset),
        Asset(quote_asset),
        Exchange('nobitex'),
        timedelta(seconds=int(resolution)),
        'create_missing_data' in args,
    )
