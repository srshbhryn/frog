import datetime

from frog.types import Pair, Asset, Price

from tadpoles.prices import Oracle
from tadpoles.types import Exchange


def test_oracle():
    oracle = Oracle(Exchange.NOBITEX)
    very_long_time_ago = datetime.datetime.fromtimestamp(11)
    assert oracle.get_price(Pair(Asset.BTC, Asset.RLS), very_long_time_ago) is None
    some_time_with_data = datetime.datetime.fromtimestamp(
        1700697666
    )  # note that it depends on running of scripts/collect_nobitex_candles.py
    assert oracle.get_price(Pair(Asset.BTC, Asset.RLS), some_time_with_data) == Price(1886348866)
