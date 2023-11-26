import datetime
import decimal

from frog.types import Asset

from tadpoles.pairtrading.pairtrading import PairTradingSimulation
from tadpoles.pairtrading.types import Algorithm


if __name__ == '__main__':
    algorithms = []
    for min_trading_beta in [
        decimal.Decimal('.9'),
        decimal.Decimal('.7'),
        decimal.Decimal('.5'),
        decimal.Decimal('0'),
        decimal.Decimal('-1'),
        decimal.Decimal('-.02'),
    ]:
        for pricing_factor in [
            decimal.Decimal('1'),
            decimal.Decimal('1.001'),
            decimal.Decimal('1.002'),
            decimal.Decimal('1.005'),
            decimal.Decimal('.999'),
            decimal.Decimal('.995'),
        ]:
            for wait_period in [
                datetime.timedelta(minutes=60),
                datetime.timedelta(minutes=30),
                datetime.timedelta(minutes=120),
                datetime.timedelta(minutes=240),
            ]:
                for trading_threshold in [
                    decimal.Decimal('.0001'),
                    decimal.Decimal('.0002'),
                    decimal.Decimal('.0003'),
                    decimal.Decimal('.0004'),
                    decimal.Decimal('.0005'),
                    decimal.Decimal('.001'),
                ]:
                    for regression_len in [
                        10,
                        20,
                        30,
                        50,
                        120,
                        200,
                        500,
                    ]:
                        for regression_delta in [
                            datetime.timedelta(minutes=1),
                            datetime.timedelta(minutes=2),
                            datetime.timedelta(minutes=5),
                            datetime.timedelta(minutes=10),
                        ]:
                            for long_asset, short_asset in [
                                (Asset.BTC, Asset.ETH),
                                (Asset.ETH, Asset.BTC),
                                (Asset.BTC, Asset.SHIB),
                                (Asset.BTC, Asset.DOGE),
                                (Asset.DOGE, Asset.ETH),
                                (Asset.SHIB, Asset.ETH),
                                (Asset.SHIB, Asset.DOGE),
                                (Asset.DOGE, Asset.SHIB),
                            ]:
                                for quote_asset in [Asset.RLS, Asset.USDT]:
                                    algorithms.append(
                                        Algorithm(
                                            min_trading_beta=min_trading_beta,
                                            pricing_factor=pricing_factor,
                                            wait_period=wait_period,
                                            trading_threshold=trading_threshold,
                                            regression_len=regression_len,
                                            regression_delta=regression_delta,
                                            long_asset=long_asset,
                                            short_asset=short_asset,
                                            quote_asset=quote_asset,
                                        )
                                    )

    start_timestamp = datetime.datetime(2023, 1, 1, 0, 0, 0, 0)
    end_timestamp = start_timestamp + datetime.timedelta(days=10 * 30)
    for k, algorithm in enumerate(algorithms):
        print(f'{datetime.datetime.now()}\t{k +1}\t{len(algorithms)}')
        PairTradingSimulation(algorithm, start_timestamp, end_timestamp).run()
