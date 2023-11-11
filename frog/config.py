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

ALL_PAIRS: list[Pair] = (
    [Pair(Asset.USDT, Asset.RLS)]
    + [Pair(asset, Asset.RLS) for asset in Asset if not asset in [Asset.USDT, Asset.RLS]]
    + [Pair(asset, Asset.USDT) for asset in Asset if not asset in [Asset.USDT, Asset.RLS]]
)


LOG_LEVEL = logging._nameToLevel.get(  # pylint: disable=protected-access
    os.getenv('LOG_LEVEL') or 'INFO' if IS_PROD else 'DEBUG'
)

NOBITEX_TOKEN = os.getenv('NOBITEX_TOKEN', default='')
NOBITEX_LEVERAGE = int(os.getenv('NOBITEX_LEVERAGE', default='1'))
