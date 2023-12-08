import datetime

from frog.types import Pair, Asset, Price

from tadpoles.prices import Oracle
from tadpoles.types import Exchange


def test_get_price():
    oracle = Oracle(Exchange.NOBITEX, Pair(Asset.BTC, Asset.RLS))
    very_long_time_ago = datetime.datetime.fromtimestamp(11)
    assert oracle.get_price(very_long_time_ago) is None
    some_time_with_data = datetime.datetime.fromtimestamp(
        1697401740
    )  # note that it depends on running of scripts/collect_nobitex_candles.py
    assert oracle.get_price(some_time_with_data) == Price(1388027061)


def test_get_time_range_min_and_max_prices():
    oracle = Oracle(Exchange.NOBITEX, Pair(Asset.BTC, Asset.RLS))
    very_long_time_ago = datetime.datetime.fromtimestamp(11)
    min_price, max_price = oracle.get_timerange_min_and_max_prices(
        very_long_time_ago,
        very_long_time_ago,
    )
    assert min_price is None and max_price is None
    some_time_with_data = datetime.datetime.fromtimestamp(
        1697401740
    )  # note that it depends on running of scripts/collect_nobitex_candles.py

    min_price, max_price = oracle.get_timerange_min_and_max_prices(
        some_time_with_data,
        some_time_with_data + datetime.timedelta(hours=3),
    )
    assert min_price == Price(1384006002) and max_price == Price(1396730800)
