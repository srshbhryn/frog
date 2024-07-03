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

from frog.types import Asset

from tadpoles.timescaledb import get_db, get_engine, delete_db_and_engine
from tadpoles.prices.models import BinanceCandle, BinanceCandleFile


_BACK_OFF_PERIOD = 60
_DATA_DIR = '/tmp/'


@dataclasses.dataclass
class _Error:
    message: str


Error = typing.Optional[_Error]


failed_download_error = _Error('cant download the file')
no_such_file_error = _Error('no such file')


class CandleDataKwargs(typing.TypedDict):
    base_asset: Asset
    quote_asset: Asset
    date: datetime.date
    resolution: datetime.timedelta


def get_candle_signature(**kwargs: CandleDataKwargs):
    symbol = str(kwargs['base_asset']).upper() + str(kwargs['quote_asset']).upper()
    if typing.TYPE_CHECKING:
        assert isinstance(kwargs['date'], datetime.date)
    date = kwargs['date'].isoformat()
    if typing.TYPE_CHECKING:
        assert isinstance(kwargs['resolution'], datetime.timedelta)
    resolution_total_seconds = kwargs['resolution'].total_seconds()
    def get_resolution_str():
        for time_unit, timedelta_key in [
            ('d', 'days'),
            ('h', 'hours'),
            ('m', 'minutes'),
            ('s', 'seconds'),
        ]:
            time_unit_total_seconds = datetime.timedelta(**{timedelta_key: 1}).total_seconds()
            if resolution_total_seconds >= time_unit_total_seconds:
                assert int(resolution_total_seconds) % int(time_unit_total_seconds) == 0
                return f'{int(resolution_total_seconds / time_unit_total_seconds)}{time_unit}'
        raise ValueError('invalid candle resolution')
    return '-'.join([symbol, get_resolution_str(), date])


def get_candle_data_file_path(**kwargs: CandleDataKwargs):
    return f'{_DATA_DIR}{get_candle_signature(**kwargs)}.zip'


def does_file_exists(filepath: str) -> bool:
    return 0 == subprocess.call(
        ['ls', filepath],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )


def does_data_is_stored_in_db(**kwargs: CandleDataKwargs) -> bool:
    return get_db().query(
        get_db().query(BinanceCandleFile).filter(
            BinanceCandleFile.date == kwargs['date'],
            BinanceCandleFile.resolution == kwargs['resolution'],
            BinanceCandleFile.base_asset == kwargs['base_asset'],
            BinanceCandleFile.quote_asset == kwargs['quote_asset'],
        ).exists()
    ).scalar()


def download_binance_candle_data(**kwargs: CandleDataKwargs) -> Error:
    signature = get_candle_signature(**kwargs)
    symbol, resolution, *_ = signature.split('-')
    url_prefix = 'https://data.binance.vision/data/spot/daily/klines/'
    url = f'{url_prefix}{symbol}/{resolution}/{signature}.zip'
    result = subprocess.run(
        ['wget', url, '-P', _DATA_DIR],
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return _Error(str(result.stderr))
    return None


def download_or_unzip_csv_file(**kwargs: CandleDataKwargs) -> Error:
    file_path = get_candle_data_file_path(**kwargs)
    if does_file_exists(file_path):
        return None
    return download_binance_candle_data(**kwargs)


def read_file(**candle_kwargs: CandleDataKwargs) -> list[BinanceCandle]:
    filepath = get_candle_data_file_path(**candle_kwargs)
    process = subprocess.run(['unzip', '-p', filepath], stdout=subprocess.PIPE, check=False)
    raw_data = str(process.stdout.decode()).split('\n')
    def convert_raw_data_to_entity(raw_line: str) -> BinanceCandle:
        (
            raw_open_time,
            raw_open_price,
            raw_max_price,
            raw_min_price,
            raw_close_price,
            raw_volume,
            _,
            raw_quote_value,
            raw_trade_count,
            raw_take_buy_base_volume,
            raw_take_buy_quote_volume,
        ) = raw_line.split(',')[:-1]
        return BinanceCandle(
            base_asset=candle_kwargs['base_asset'],
            quote_asset=candle_kwargs['quote_asset'],
            open_time=datetime.datetime.fromtimestamp(int(raw_open_time) / 1000, tz=pytz.UTC),
            resolution=candle_kwargs['resolution'],
            min_price=decimal.Decimal(raw_min_price),
            max_price=decimal.Decimal(raw_max_price),
            open_price=decimal.Decimal(raw_open_price),
            close_price=decimal.Decimal(raw_close_price),
            volume=decimal.Decimal(raw_volume),
            quote_value=decimal.Decimal(raw_quote_value),
            trade_count=int(raw_trade_count),
            take_buy_base_volume=decimal.Decimal(raw_take_buy_base_volume),
            take_buy_quote_volume=decimal.Decimal(raw_take_buy_quote_volume),
        )
    return list(map(convert_raw_data_to_entity, filter(lambda line: (line != ''), raw_data)))


def collect_binance_candles(
    base_asset: Asset,
    quote_asset: Asset,
    from_date: datetime.date,
    to_date: datetime.date,
    resolution: datetime.timedelta,
):
    delete_db_and_engine()
    one_day = datetime.timedelta(days=1)
    from_date -= one_day
    while from_date < to_date:
        from_date += one_day
        candle_kwargs = CandleDataKwargs(
            base_asset=base_asset,
            quote_asset=quote_asset,
            date=from_date,
            resolution=resolution,
        )
        if does_data_is_stored_in_db(**candle_kwargs):
            continue
        error = download_or_unzip_csv_file(**candle_kwargs)
        if error is not None:
            print(error.message)
            time.sleep(_BACK_OFF_PERIOD)
            from_date -= one_day
            continue
        candles = read_file(**candle_kwargs)
        with Session(get_engine()) as session:
            session.add_all(candles)
            session.add(BinanceCandleFile(
                date=from_date,
                resolution=resolution,
                base_asset=base_asset,
                quote_asset=quote_asset,
            ))
            session.commit()


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
        process = multiprocessing.Process(target=collect_binance_candles, args=(
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
