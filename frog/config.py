import logging
import os
import pathlib

from frog.types import Asset, Pair

IS_PROD = os.getenv('ENV') == 'PROD'

DATA_DIR = pathlib.Path(__file__).parent.parent.joinpath('data/')

HIGHWAY_HOST = '127.0.0.1'
SQUARE_HOST = '127.0.0.1'

HIGHWAY_XSUB_PORT = '4142'
HIGHWAY_XPUB_PORT = '4143'

if IS_PROD:
    DATA_DIR = pathlib.Path('/data/')

ALL_PAIRS: list[Pair] = [
    Pair(Asset.BTC, Asset.RLS),
    Pair(Asset.BTC, Asset.USDT),
    Pair(Asset.ETH, Asset.RLS),
    Pair(Asset.ETH, Asset.USDT),
]

LOG_LEVEL = logging._nameToLevel.get(os.getenv('LOG_LEVEL') or 'INFO' if IS_PROD else 'DEBUG')


NOBITEX_TOKEN = os.getenv('NOBITEX_TOKEN', default='')
