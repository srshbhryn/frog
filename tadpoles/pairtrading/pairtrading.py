import dataclasses
import datetime
import decimal

from frog.types import Asset, Amount, Value, Price, Pair, Regression
from tadpoles.prices import Oracle


@dataclasses.dataclass
class Algorithm:
    min_trading_beta: decimal.Decimal
    pricing_factor: decimal.Decimal
    wait_period: datetime.timedelta
    trading_threshold: decimal.Decimal
    regression_len: int
    regression_delta: datetime.timedelta  # should be integer number of minutes
    long_asset: Asset
    short_asset: Asset
    quote_asset: Asset

    def __init__(
        self,
        min_trading_beta,
        pricing_factor,
        trading_threshold,
        wait_period,
        regression_len,
        regression_delta,
        long_asset,
        short_asset,
        quote_asset,
    ):
        self.min_trading_beta = min_trading_beta
        self.pricing_factor = pricing_factor
        self.trading_threshold = trading_threshold
        self.wait_period = wait_period
        self.regression_len = regression_len
        number_of_regression_delta_minutes = regression_delta / datetime.timedelta(minutes=1)
        assert int(number_of_regression_delta_minutes) == number_of_regression_delta_minutes
        self.regression_delta = regression_delta
        self.long_asset = long_asset
        self.short_asset = short_asset
        self.quote_asset = quote_asset


@dataclasses.dataclass
class Result:
    timestamp: datetime.datetime
    regression: Regression
    did_short_trade_fill: bool
    did_long_trade_fill: bool
    gain: decimal.Decimal


class PairTradingSimulation:
    def __init__(
        self,
        algorithm_parameters: AlgorithmParameters,
        start_at: datetime.datetime,
        end_at: datetime.datetime,
        prices_oracle: Oracle,
    ) -> None:
        self.start_at = start_at
        self.end_at = end_at
        self.algorithm_parameters = algorithm_parameters
        self.prices_oracle = prices_oracle
        self.simulation_timestamp = start_at.timestamp()
        self.results: list[Result] = []

    def get_prices(self):
        pass
