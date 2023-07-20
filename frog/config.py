
import os
import pathlib

from frog.types import Pair, Asset


IS_PROD = os.getenv('ENV') == 'PROD'

ORDERBOOK_URI = 'tcp://127.0.0.1:5212'
TRADECOLLECTOR_URI = 'tcp://127.0.0.1:5213'
PRICESERVICE_URI = 'tcp://127.0.0.1:5214'

DATA_DIR = pathlib.Path(__file__).parent.parent.joinpath('data/')
LOGS_DIR = pathlib.Path(__file__).parent.parent.joinpath('logs/')


if IS_PROD:
    ORDERBOOK_URI = 'tcp://orderbook:1212'
    TRADECOLLECTOR_URI = 'tcp://tradecollector:1212'
    PRICESERVICE_URI = 'tcp://tradestore:1212'
    DATA_DIR = '/data/'
    LOGS_DIR = '/logs/'



ALL_PAIRS: list[Pair] = [
    Pair(Asset.BTC, Asset.RLS),
    Pair(Asset.BTC, Asset.USDT),
    Pair(Asset.ETH, Asset.RLS),
    Pair(Asset.ETH, Asset.USDT),
]
