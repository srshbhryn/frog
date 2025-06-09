import multiprocessing
import itertools
import dataclasses
import typing
import datetime
import tqdm

import sqlalchemy


from frog.types import Asset

from tadpoles.prices.utils import get_prices
from tadpoles.types import Exchange
from tadpoles.timescaledb import get_db

from tadpoles.railer import simulation_zero, SimZero, SimResult, SimPriceQuality, SimParams, create_sim


# def build_exists_query(model, dataclass_obj):
#     filters = []
#     for field, value in asdict(dataclass_obj).items():
#         if hasattr(model, field):
#             filters.append(getattr(model, field) == value)
#     return 
# def check_exists(session, model, dataclass_obj):
#     stmt = build_exists_query(model, dataclass_obj)
#     return session.scalar(stmt)


def do_sim(params):
        try:
            db = get_db()
            if db.scalar(sqlalchemy.select(sqlalchemy.exists().where(sqlalchemy.and_(*[
                getattr(SimZero, key) == value
                for key, value in dataclasses.asdict(params).items()
            ])))):
                return
            result, price_quality = simulation_zero(params)
            db.add(create_sim(
                params,
                price_quality,
                result,
            ))
            db.commit()
        except Exception as e:
            print('an error occurred', e)

def run_simulation_zero():
    data_start_time = datetime.datetime.fromisoformat('2023-12-31 20:30:00.000')
    data_end_time = datetime.datetime.fromisoformat('2025-04-30 20:29:00.000')
    def gen_params(
        starttime: datetime.datetime,
        period: datetime.timedelta,
        sell_buy_threshold: float,
        buy_sell_threshold: float,
    ) -> SimResult:
        return SimParams(
            base_asset=Asset.USDT,
            quote_asset=Asset.RLS,
            exchange_0=Exchange.WALLEX,
            exchange_1=Exchange.OMPFINEX,
            exchange_0_fee=0.02,
            exchange_1_fee=0.01,
            timestamp=starttime,
            simulation_period=period,
            sell_buy_threshold=sell_buy_threshold,
            buy_sell_threshold=buy_sell_threshold,
            sell_buy_amount=1,
            buy_sell_amount=1,
            exchange_0_initial_base=1_000,
            exchange_0_initial_quote=60_000_000,
            exchange_1_initial_base=1_000,
            exchange_1_initial_quote=60_000_000,
        )
    periods = [
        datetime.timedelta(days=d)
        for d in [1,2, 3, 5]
    ]

    step = 0.0002
    start = 0.99
    end = 1.01
    values = [start + i * step for i in range(int((end - start) / step) + 1)]

    threasholds = list(itertools.product(values, repeat=2))
    params_list = []
    for period in periods:
        for sell_buy_threshold, buy_sell_threshold in threasholds:
            start_time = data_start_time
            while start_time < data_end_time - period:
                params_list.append(gen_params(start_time, period, sell_buy_threshold, buy_sell_threshold))
                params_list.append(gen_params(start_time, period, buy_sell_threshold, sell_buy_threshold))
                start_time += period

    print('there are', len(params_list), 'simulations to do')
    ctx = multiprocessing.get_context('spawn')
    with ctx.Pool(16) as pool:
        pool.map(do_sim, params_list)


if __name__ == '__main__':
    run_simulation_zero()
