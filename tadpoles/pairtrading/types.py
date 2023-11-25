import dataclasses
import datetime
import decimal
import typing

from frog.types import Asset, Regression, Amount

from tadpoles.pairtrading.regression import RegressionDetail

from .db import AlgorithmEntity, ResultEntity


class AlgorithmEntityKwargs(typing.TypedDict):
    min_trading_beta: decimal.Decimal
    pricing_factor: decimal.Decimal
    wait_period: int
    trading_threshold: decimal.Decimal
    regression_len: int
    regression_delta: int
    long_asset: str
    short_asset: str
    quote_asset: str


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

    def as_entity_kwargs(self) -> AlgorithmEntityKwargs:
        return AlgorithmEntityKwargs(
            min_trading_beta=self.min_trading_beta,
            pricing_factor=self.pricing_factor,
            wait_period=int(self.wait_period.total_seconds()),
            trading_threshold=self.trading_threshold,
            regression_len=self.regression_len,
            regression_delta=int(self.regression_delta.total_seconds()),
            long_asset=self.long_asset.value,
            short_asset=self.short_asset.value,
            quote_asset=self.quote_asset.value,
        )


class ResultEntityKwargs(typing.TypedDict):
    algorithm_id: int
    timestamp: int
    regression_alpha: decimal.Decimal
    regression_beta: decimal.Decimal
    regression_long_price_normalizer: decimal.Decimal
    regression_short_price_normalizer: decimal.Decimal
    regression_number_of_long_prices: int
    regression_number_of_short_prices: int
    regression_number_of_timestamps_intersection_set: int
    added_long_asset_amount: Amount
    added_short_asset_amount: Amount
    added_quote_asset_amount: Amount
    did_short_trade_fill: bool
    did_long_trade_fill: bool


@dataclasses.dataclass
class Result:
    timestamp: datetime.datetime
    regression: Regression
    regression_detail: RegressionDetail
    did_short_trade_fill: bool
    did_long_trade_fill: bool
    added_long_asset_amount: Amount
    added_short_asset_amount: Amount
    added_quote_asset_amount: Amount

    def as_entity_kwargs(self, algorithm_id: int) -> ResultEntityKwargs:
        return ResultEntityKwargs(
            algorithm_id=algorithm_id,
            timestamp=self.timestamp,
            regression_alpha=self.regression.alpha,
            regression_beta=self.regression.beta,
            regression_long_price_normalizer=self.regression.long_price_normalizer.as_decimal(),
            regression_short_price_normalizer=self.regression.short_price_normalizer.as_decimal(),
            regression_number_of_long_prices=self.regression_detail.number_of_long_prices,
            regression_number_of_short_prices=self.regression_detail.number_of_short_prices,
            regression_number_of_timestamps_intersection_set=self.regression_detail.number_of_timestamps_intersection_set,
            did_short_trade_fill=self.did_short_trade_fill,
            did_long_trade_fill=self.did_long_trade_fill,
            added_long_asset_amount=self.added_long_asset_amount.as_decimal(),
            added_short_asset_amount=self.added_short_asset_amount.as_decimal(),
            added_quote_asset_amount=self.added_quote_asset_amount.as_decimal(),
        )
