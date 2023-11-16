import logging
import time
import typing
import datetime
from decimal import Decimal
import multiprocessing

from frog import config
from frog.types import Asset, Value
from frog.cores.eye import Eye


class EyeConf(typing.TypedDict):
    regression_len: int
    trade_threshold: Decimal
    pricing_factor: Decimal
    wait_period: datetime.timedelta
    long_asset: Asset
    short_asset: Asset
    quote_asset: Asset
    base_trade_value: Value
    client_identity: str


def target(conf):
    Eye(**conf).run()


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn', True)
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=config.LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    configs = []
    counter = 0
    for reg_len in [60, 120, 180]:
        for trade_threshold in [Decimal('0.001'), Decimal('0.002'), Decimal('0.003')]:
            for long, short in [
                (Asset.BTC, Asset.ETH),
                (Asset.BTC, Asset.DOGE),
                (Asset.BTC, Asset.SHIB),
                (Asset.ETH, Asset.BTC),
                (Asset.ETH, Asset.DOGE),
                (Asset.ETH, Asset.SHIB),
                (Asset.DOGE, Asset.SHIB),
                (Asset.SHIB, Asset.DOGE),
                (Asset.DOGE, Asset.BTC),
            ]:
                for quote, value in [
                    (Asset.RLS, Value('500_000_0')),
                    (Asset.USDT, Value('10')),
                ]:
                    counter += 1
                    name = f'eye{counter}_'
                    conf = EyeConf(
                        regression_len=reg_len,
                        trade_threshold=trade_threshold,
                        pricing_factor=Decimal('1.0'),
                        wait_period=datetime.timedelta(minutes=60),
                        long_asset=long,
                        short_asset=short,
                        quote_asset=quote,
                        base_trade_value=value,
                        client_identity=name,
                    )
                    logging.info(conf)
                    configs.append(conf)

    for conf in configs:
        multiprocessing.Process(
            target=target,
            args=(conf,),
            daemon=True,
        ).start()
    while True:
        time.sleep(120)
