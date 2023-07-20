
import os
import pathlib

from frog.types import Pair, Asset


class Config:
    orderbook_port = os.getenv('ORDERBOOK_PORT')
    tradecollector_port = os.getenv('TRADECOLLECTOR_PORT')
    priceservice_port = os.getenv('PRICESERVICE_PORT')


ROOT_DIR = pathlib.Path(__file__).parent.parent
DATA_DIR = ROOT_DIR.joinpath('data/')
LOGS_DIR = ROOT_DIR.joinpath('logs/')


ALL_PAIRS: list[Pair] = [
    Pair(Asset.BTC, Asset.RLS),
    Pair(Asset.BTC, Asset.USDT),
    Pair(Asset.ETH, Asset.RLS),
    Pair(Asset.ETH, Asset.USDT),
]
