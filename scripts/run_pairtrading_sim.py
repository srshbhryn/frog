import multiprocessing
import logging
import datetime
import decimal

from frog.types import Asset

from tadpoles.pairtrading.pairtrading import PairTradingSimulation
from tadpoles.pairtrading.types import Algorithm


def target(algorithms, start_timestamp, end_timestamp, queue: multiprocessing.Queue):
    for k, alg in algorithms:
        try:
            print(f'{datetime.datetime.now()}\tstart\t{k}')
            PairTradingSimulation(alg, start_timestamp, end_timestamp).run()
            print(f'{datetime.datetime.now()}\tend\t{k}')
        except:
            logging.exception('algorithm %d has failed', k)
    queue.put(b'1')


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn', True)
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    algorithms = []
    for min_trading_beta in [
        decimal.Decimal('.8'),
        decimal.Decimal('0'),
    ]:
        for pricing_factor in [
            decimal.Decimal('1'),
            decimal.Decimal('1.002'),
            decimal.Decimal('1.005'),
        ]:
            for wait_period in [
                datetime.timedelta(minutes=60),
                datetime.timedelta(minutes=30),
            ]:
                for trading_threshold in [
                    decimal.Decimal('.0001'),
                    decimal.Decimal('.0002'),
                    decimal.Decimal('.0005'),
                    decimal.Decimal('.001'),
                ]:
                    for regression_len in [
                        10,
                        50,
                        100,
                        200,
                    ]:
                        for regression_delta in [
                            datetime.timedelta(minutes=1),
                            datetime.timedelta(minutes=5),
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
    target_args = list(enumerate(algorithms))

    N = 5
    queue = multiprocessing.Queue()
    indexes = [i * int(len(algorithms) / N) for i in range(N)]
    indexes += [len(algorithms)]
    for i, j in zip(indexes[:-1], indexes[1:]):
        multiprocessing.Process(
            target=target,
            args=(target_args[i:j], start_timestamp, end_timestamp, queue),
            daemon=True,
        ).start()

    for _ in range(N):
        _ = queue.get()
