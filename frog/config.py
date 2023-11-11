import logging
import os
import pathlib

from frog.types import Asset, Pair

IS_PROD = os.getenv('ENV') == 'PROD'

DATA_DIR = pathlib.Path(__file__).parent.parent.joinpath('data/')

if IS_PROD:
    DATA_DIR = pathlib.Path('/data/')

HIGHWAY_HOST = os.getenv('HIGHWAY_HOST') or 'highway'
HIGHWAY_XSUB_PORT = os.getenv('HIGHWAY_XSUB_PORT') or '1213'
HIGHWAY_XPUB_PORT = os.getenv('HIGHWAY_XPUB_PORT') or '1214'

ALL_PAIRS: list[Pair] = [
    Pair(Asset.BTC, Asset.RLS),
    Pair(Asset.BTC, Asset.USDT),
    Pair(Asset.ETH, Asset.RLS),
    Pair(Asset.ETH, Asset.USDT),
    Pair(Asset.DOGE, Asset.RLS),
    Pair(Asset.DOGE, Asset.USDT),
    Pair(Asset.SHIB, Asset.RLS),
    Pair(Asset.SHIB, Asset.USDT),
]

LOG_LEVEL = logging._nameToLevel.get(  # pylint: disable=protected-access
    os.getenv('LOG_LEVEL') or 'INFO' if IS_PROD else 'DEBUG'
)

NOBITEX_TOKEN = os.getenv('NOBITEX_TOKEN', default='')
NOBITEX_LEVERAGE = int(os.getenv('NOBITEX_LEVERAGE', default='1'))
