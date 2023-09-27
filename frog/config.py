import logging
import os
import pathlib

from frog.types import Asset, Pair

IS_PROD = os.getenv('ENV') == 'PROD'

DATA_DIR = pathlib.Path(__file__).parent.parent.joinpath('data/')

if IS_PROD:
    DATA_DIR = pathlib.Path('/data/')

HIGHWAY_HOST = 'e14810cb-6984-4e34-b677-1dc345f2b7f9.hsvc.ir'
HIGHWAY_XSUB_PORT = '31001'
HIGHWAY_XPUB_PORT = '30566'

SQUARE_HOST = '0bdad864-b7a4-416a-912c-7ca923bb6e34.hsvc.ir'
SQUARE_FRONTEND_PORT = '31605'
SQUARE_BACKEND_PORT = '30500'

if IS_PROD:
    HIGHWAY_HOST = 'highway.sorushbahariyan-frog.svc'
    HIGHWAY_XSUB_PORT = '4142'
    HIGHWAY_XPUB_PORT = '4143'

    SQUARE_HOST = 'square.sorushbahariyan-frog.svc'
    SQUARE_FRONTEND_PORT = '1616'
    SQUARE_BACKEND_PORT = '1212'


ALL_PAIRS: list[Pair] = [
    Pair(Asset.BTC, Asset.RLS),
    Pair(Asset.BTC, Asset.USDT),
    Pair(Asset.ETH, Asset.RLS),
    Pair(Asset.ETH, Asset.USDT),
]

LOG_LEVEL = logging._nameToLevel.get(os.getenv('LOG_LEVEL') or 'INFO' if IS_PROD else 'DEBUG')


NOBITEX_TOKEN = os.getenv('NOBITEX_TOKEN', default='')
