import datetime
import decimal

from frog.types import Asset

from tadpoles.pairtrading.pairtrading import PairTradingSimulation
from tadpoles.pairtrading.types import Algorithm


if __name__ == '__main__':
    algorithm = Algorithm(
        min_trading_beta=decimal.Decimal('.7'),
        pricing_factor=decimal.Decimal('1.002'),
        wait_period=datetime.timedelta(minutes=50),
        trading_threshold=decimal.Decimal('.0002'),
        regression_len=120,
        regression_delta=datetime.timedelta(minutes=1),
        long_asset=Asset.BTC,
        short_asset=Asset.DOGE,
        quote_asset=Asset.RLS,
    )
    start_timestamp = datetime.datetime(2023, 5, 1, 0, 0, 0, 0)
    end_timestamp = start_timestamp + datetime.timedelta(days=5 * 30)

    sim = PairTradingSimulation(algorithm, start_timestamp, end_timestamp)
    sim.run()
