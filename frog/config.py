import logging
import os
import pathlib

from frog.types import Pair, Asset


IS_PROD = os.getenv('ENV') == 'PROD'

ORDERBOOK_BIND_URI = 'tcp://127.0.0.1:5212'
ORDERBOOK_URI = 'tcp://127.0.0.1:5212'

TRADECOLLECTOR_BIND_URI = 'tcp://127.0.0.1:5213'
TRADECOLLECTOR_URI = 'tcp://127.0.0.1:5213'

ANALYSISSERVICE_BIND_URI = 'tcp://127.0.0.1:5217'
ANALYSISSERVICE_URI = 'tcp://127.0.0.1:5217'


DATA_DIR = pathlib.Path(__file__).parent.parent.joinpath('data/')


if IS_PROD:

    ORDERBOOK_BIND_URI = 'tcp://*:1212'
    ORDERBOOK_URI = 'tcp://orderbook:1212'

    TRADECOLLECTOR_BIND_URI = 'tcp://*:1212'
    TRADECOLLECTOR_URI = 'tcp://tradecollector:1212'

    PRICESERVICE_BIND_URI = 'tcp://*:1212'
    PRICESERVICE_URI = 'tcp://tradestore:1212'

    ANALYSISSERVICE_BIND_URI = 'tcp://*:1212'
    ANALYSISSERVICE_URI = 'tcp://analysis:1212'

    DATA_DIR = pathlib.Path('/data/')


ALL_PAIRS: list[Pair] = [
    Pair(Asset.BTC, Asset.RLS),
    Pair(Asset.BTC, Asset.USDT),
    Pair(Asset.ETH, Asset.RLS),
    Pair(Asset.ETH, Asset.USDT),
]

LOG_LEVEL = logging._nameToLevel.get(os.getenv('LOG_LEVEL') or 'INFO' if IS_PROD else 'DEBUG')
