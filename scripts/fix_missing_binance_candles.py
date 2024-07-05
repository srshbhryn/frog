import multiprocessing
import decimal
import subprocess
import dataclasses
import typing
import datetime
import logging
import time
import sys

import pytz
from sqlalchemy.orm import Session
from sqlalchemy import cast, Date

from frog.types import Asset

from tadpoles.timescaledb import get_db, get_engine, delete_db_and_engine
from tadpoles.prices.models import BinanceCandle, BinanceCandleFile


def get_avg_candle(candles: list[BinanceCandle]):
    def get_avg_attrs(key: str):
        return sum([getattr(candle, key) for candle in candles]) / len(candles)
    return BinanceCandle(
        base_asset=candles[0].base_asset,
        quote_asset=candles[0].quote_asset,
        open_time=candles[0].quote_asset,
        resolution=candles[0].resolution,
        min_price=get_avg_attrs('min_price'),
        max_price=get_avg_attrs('max_price'),
        open_price=get_avg_attrs('open_price'),
        close_price=get_avg_attrs('close_price'),
        volume=get_avg_attrs('volume'),
        quote_value=get_avg_attrs('quote_value'),
        trade_count=int(get_avg_attrs('trade_count')),
        take_buy_base_volume=get_avg_attrs('take_buy_base_volume'),
        take_buy_quote_volume=get_avg_attrs('take_buy_quote_volume'),
    )


@dataclasses.dataclass
class _Error:
    message: str


Error = typing.Optional[_Error]


class CandleDataKwargs(typing.TypedDict):
    base_asset: Asset
    quote_asset: Asset
    date: datetime.date
    resolution: datetime.timedelta


def fix_missing_candles(
    base_asset: Asset,
    quote_asset: Asset,
    from_date: datetime.date,
    to_date: datetime.date,
    resolution: datetime.timedelta,
):
    delete_db_and_engine()
    db = get_db()
    downloaded_files = db.query(BinanceCandleFile).filter(
        BinanceCandleFile.date <= to_date,
        BinanceCandleFile.date >= from_date,
        BinanceCandleFile.resolution == resolution,
        BinanceCandleFile.base_asset == base_asset,
        BinanceCandleFile.quote_asset == quote_asset,
    ).order_by(BinanceCandleFile.date).all()

    date_to_downloaded_file_map = dict(map(lambda file_data: (file_data.date, file_data), downloaded_files))
    number_of_candles_per_day = int(datetime.timedelta(days=1).total_seconds() / resolution.total_seconds())
    one_day = datetime.timedelta(days=1)
    date = from_date - one_day
    while date < to_date:
        date += one_day
        if date not in date_to_downloaded_file_map:
            logging.warning('%s-%s data is not downloaded for %s', base_asset, quote_asset, date.isoformat())
            continue

        candles_filter = [
            BinanceCandle.resolution == resolution,
            cast(BinanceCandle.open_time, Date) == date,
            BinanceCandle.base_asset == base_asset,
            BinanceCandle.quote_asset == quote_asset,
        ]
        existing_number_of_candles = db.query(BinanceCandle).filter(*candles_filter).count()
        if existing_number_of_candles == number_of_candles_per_day:
            continue
        logging.warning(
            '%s-%s data for %s is missing %d candles. adding missing candles...',
            base_asset,
            quote_asset,
            date.isoformat(),
            number_of_candles_per_day - existing_number_of_candles,
        )

        file_candles = db.query(BinanceCandle).filter(*candles_filter)

        first_open_timestamp = datetime.datetime.combine(date, datetime.time.min)
        last_open_timestamp = datetime.datetime.combine(date + one_day, datetime.time.min) - resolution

        # fix if first candle is missing
        first_candle = file_candles.order_by(BinanceCandle.open_time).first()
        if not first_candle.open_time == first_open_timestamp:
            real_first_candle = get_avg_candle([first_candle])
            real_first_candle.open_time = first_open_timestamp
            db.add(real_first_candle)
            db.commit()

        # fix if last candle is missing
        last_candle = file_candles.order_by(BinanceCandle.open_time.desc()).first()
        if not last_candle.open_time == last_open_timestamp:
            real_last_candle = get_avg_candle([last_candle])
            real_last_candle.open_time = last_open_timestamp
            db.add(real_last_candle)
            db.commit()

        # fix other candles
        open_time_to_candles = dict(map(lambda c: (c.open_time, c), file_candles.all()))
        open_time_index = first_open_timestamp
        while open_time_index < last_open_timestamp:
            open_time_index += resolution
            if open_time_index in open_time_to_candles:
                continue
            next_open_time = open_time_index
            while next_open_time not in open_time_to_candles:
                next_open_time += resolution
            previous_open_time = open_time_index - resolution
            next_candle = open_time_to_candles[next_open_time]
            previous_candle = open_time_to_candles[previous_open_time]
            candle = get_avg_candle([next_candle, previous_candle])
            candle.open_time = open_time_index
            db.add(candle)
            open_time_to_candles[open_time_index] = candle

        db.commit()


if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S',
    )
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

    processes = []
    for base_asset, quote_asset in symbols:
        process = multiprocessing.Process(target=fix_missing_candles, args=(
            base_asset,
            quote_asset,
            from_date,
            to_date,
            resolution,
        ))
        process.start()
        processes.append(process)

    for process in processes:
        process.join()
