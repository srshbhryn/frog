
import os

from frog.types import Pair, Asset


class Config:
    orderbook_port = os.getenv('ORDERBOOK_PORT')
    tradecollector_port = os.getenv('TRADECOLLECTOR_PORT')
    priceservice_port = os.getenv('PRICESERVICE_PORT')


ALL_PAIRS: list[Pair] = [
    Pair(Asset.BTC, Asset.RLS),
    Pair(Asset.BTC, Asset.USDT),
    Pair(Asset.ETH, Asset.RLS),
    Pair(Asset.ETH, Asset.USDT),
]
