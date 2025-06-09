import datetime
import dataclasses
import typing

from frog.types import Asset
from tadpoles.types import Exchange
from tadpoles.prices.utils import get_prices

from ._models import SimZero



class TradingPortfolio:
    def __init__(self,
        base: float,
        quote: float,
        fee: float,
        sell_trading_amount: float,
        buy_trading_amount: float,
    ):
        self.base = base
        self.quote = quote
        self.fee = fee
        self.sell_trading_amount = sell_trading_amount
        self.buy_trading_amount = buy_trading_amount

    def can_sell(self, price) -> bool:
        new_base = self.base - self.sell_trading_amount
        new_quote = self.quote + (self.sell_trading_amount * price) * (1 - self.fee)
        return new_base >= 0 and new_quote >= 0

    def can_buy(self, price) -> bool:
        new_base = self.base + self.buy_trading_amount * (1 - self.fee)
        new_quote = self.quote - (self.buy_trading_amount * price)
        return new_base >= 0 and new_quote >= 0

    def sell(self, price):
        self.base -= self.sell_trading_amount
        self.quote += (self.sell_trading_amount * price) * (1 - self.fee)

    def buy(self, price):
        self.base += self.buy_trading_amount * (1 - self.fee)
        self.quote -= (self.buy_trading_amount * price)

    def value_in_base(self, price):
        return self.base + self.quote / price

    def value_in_quote(self, price):
        return self.quote + self.base * price


@dataclasses.dataclass(slots=True)
class TradingDetail:
    buy_sell_trade_count: int = 0
    sell_buy_trade_count: int = 0
    buy_sell_cant_trade_count: int = 0
    sell_buy_cant_trade_count: int = 0


@dataclasses.dataclass(slots=True)
class SimParams:
    base_asset: Asset
    quote_asset: Asset
    exchange_0: Exchange
    exchange_1: Exchange
    exchange_0_fee: float
    exchange_1_fee: float
    timestamp: datetime.datetime
    simulation_period: datetime.timedelta
    sell_buy_threshold: float
    buy_sell_threshold: float
    sell_buy_amount: float
    buy_sell_amount: float
    exchange_0_initial_base: float
    exchange_0_initial_quote: float
    exchange_1_initial_base: float
    exchange_1_initial_quote: float


@dataclasses.dataclass(slots=True)
class SimPriceQuality:
    exchange_0_number_of_missing_points: int
    exchange_1_number_of_missing_points: int
    number_of_total_points: int



@dataclasses.dataclass(slots=True)
class SimResult:
    exchange_0_final_base: float
    exchange_0_final_quote: float
    exchange_1_final_base: float
    exchange_1_final_quote: float
    exchange_0_final_value_in_base: float
    exchange_0_final_value_in_quote: float
    exchange_1_final_value_in_base: float
    exchange_1_final_value_in_quote: float
    exchange_0_initial_value_in_base: float
    exchange_0_initial_value_in_quote: float
    exchange_1_initial_value_in_base: float
    exchange_1_initial_value_in_quote: float
    trading_detail_buy_sell_trade_count: int
    trading_detail_sell_buy_trade_count: int
    trading_detail_buy_sell_cant_trade_count: int
    trading_detail_sell_buy_cant_trade_count: int


def simulation_zero(
    params: SimParams,
) -> typing.Tuple[SimResult, SimPriceQuality]:
    tp_0 = TradingPortfolio(
        params.exchange_0_initial_base,
        params.exchange_0_initial_quote,
        params.exchange_0_fee,
        params.sell_buy_amount,
        params.buy_sell_amount,
    )
    tp_1 = TradingPortfolio(
        params.exchange_1_initial_base,
        params.exchange_1_initial_quote,
        params.exchange_1_fee,
        params.buy_sell_amount,
        params.sell_buy_amount,
    )
    prices_0 = get_prices(
        params.exchange_0,
        params.base_asset,
        params.quote_asset,
        params.timestamp,
        params.timestamp + params.simulation_period,
    )
    prices_1 = get_prices(
        params.exchange_1,
        params.base_asset,
        params.quote_asset,
        params.timestamp,
        params.timestamp + params.simulation_period,
    )
    exchange_0_initial_value_in_base = tp_0.value_in_base(prices_0.fixed_prices[0])
    exchange_0_initial_value_in_quote = tp_0.value_in_quote(prices_0.fixed_prices[0])
    exchange_1_initial_value_in_base = tp_1.value_in_base(prices_1.fixed_prices[0])
    exchange_1_initial_value_in_quote = tp_1.value_in_quote(prices_1.fixed_prices[0])
    detail = TradingDetail()
    for p0, p1 in zip(
        prices_0.fixed_prices,
        prices_1.fixed_prices,
    ):
        if p0 / p1 >  params.sell_buy_threshold:
            if tp_0.can_sell(p0) and tp_1.can_buy(p1):
                tp_0.sell(p0)
                tp_1.buy(p1)
                detail.sell_buy_trade_count += 1
            else:
                detail.sell_buy_cant_trade_count += 1

        if p0 / p1 < params.buy_sell_threshold:
            if tp_0.can_buy(p0) and tp_1.can_sell(p1):
                tp_0.buy(p0)
                tp_1.sell(p1)
                detail.buy_sell_trade_count += 1
            else:
                detail.buy_sell_cant_trade_count += 1

    return SimResult(
        exchange_0_final_base=tp_0.base,
        exchange_0_final_quote=tp_0.quote,
        exchange_1_final_base=tp_1.base,
        exchange_1_final_quote=tp_1.quote,
        exchange_0_final_value_in_base=tp_0.value_in_base(prices_0.fixed_prices[-1]),
        exchange_0_final_value_in_quote=tp_0.value_in_quote(prices_0.fixed_prices[-1]),
        exchange_1_final_value_in_base=tp_1.value_in_base(prices_1.fixed_prices[-1]),
        exchange_1_final_value_in_quote=tp_1.value_in_quote(prices_1.fixed_prices[-1]),
        exchange_0_initial_value_in_base=exchange_0_initial_value_in_base,
        exchange_0_initial_value_in_quote=exchange_0_initial_value_in_quote,
        exchange_1_initial_value_in_base=exchange_1_initial_value_in_base,
        exchange_1_initial_value_in_quote=exchange_1_initial_value_in_quote,
        trading_detail_buy_sell_trade_count=detail.buy_sell_trade_count,
        trading_detail_sell_buy_trade_count=detail.sell_buy_trade_count,
        trading_detail_buy_sell_cant_trade_count=detail.buy_sell_cant_trade_count,
        trading_detail_sell_buy_cant_trade_count=detail.sell_buy_trade_count,
    ), SimPriceQuality(
        prices_0.number_of_missing_points,
        prices_1.number_of_missing_points,
        len(prices_0.fixed_prices),
    )


def create_sim(
    params: SimParams,
    quality: SimPriceQuality,
    result: SimResult,
) -> SimZero:
    combined = {
        **dataclasses.asdict(params),
        **dataclasses.asdict(quality),
        **dataclasses.asdict(result),
    }
    sim_fields = {c.name for c in SimZero.__table__.columns}
    filtered = {k: v for k, v in combined.items() if k in sim_fields}
    return SimZero(**filtered)
