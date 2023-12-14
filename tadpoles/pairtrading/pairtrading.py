import dataclasses
import datetime
import decimal
import logging
import functools

from frog.types import Amount, Value, Pair, Regression
from tadpoles.prices import Oracle
from tadpoles.types import Exchange
from tadpoles.timescaledb import db

from .types import Algorithm, Result
from .models import AlgorithmEntity, ResultEntity
from .regression import linear_regression


class PairTradingSimulation:
    FEE_FACTOR = decimal.Decimal('.999')

    def __init__(
        self,
        algorithm: Algorithm,
        start_at: datetime.datetime,
        end_at: datetime.datetime,
    ) -> None:
        self.start_at = start_at
        self.end_at = end_at
        self.algorithm = algorithm
        self.long_pair_oracle = Oracle(
            Exchange.NOBITEX,
            Pair(self.algorithm.long_asset, self.algorithm.quote_asset),
        )
        self.short_pair_oracle = Oracle(
            Exchange.NOBITEX,
            Pair(self.algorithm.short_asset, self.algorithm.quote_asset),
        )

    @functools.cached_property
    def algorithm_id(self) -> int:
        entity_kwargs = self.algorithm.as_entity_kwargs()
        algorithm_entity = db.query(AlgorithmEntity).filter_by(**entity_kwargs).first()
        if algorithm_entity is None:
            algorithm_entity = AlgorithmEntity(**entity_kwargs)
            db.add(algorithm_entity)
            db.commit()
            db.refresh(algorithm_entity)

        return algorithm_entity.id

    def run(self):
        sim_delta = self.algorithm.regression_len * self.algorithm.regression_delta
        for timestamp in [self.start_at + i * sim_delta for i in range(int((self.end_at - self.start_at) / sim_delta))]:
            self._run_for(timestamp)

    def _run_for(self, timestamp: datetime.datetime) -> None:
        if db.query(
            db.query(ResultEntity).filter_by(algorithm_id=self.algorithm_id, timestamp=timestamp).exists()
        ).scalar():
            logging.warning(
                'Re-running simulation for algorithm #%d and "%s".',
                self.algorithm_id,
                timestamp.isoformat(),
            )
            return

        to_timestamp = timestamp
        from_timestamp = to_timestamp - self.algorithm.regression_delta * self.algorithm.regression_len
        regression, regression_detail = self._get_regression(from_timestamp, to_timestamp)
        if regression.beta < self.algorithm.min_trading_beta:
            return

        long_price = self.long_pair_oracle.get_price(to_timestamp)
        short_price = self.short_pair_oracle.get_price(to_timestamp)

        if long_price is None or short_price is None:
            return

        residual = (
            long_price / regression.long_price_normalizer
            - regression.alpha
            - regression.beta * (short_price / regression.short_price_normalizer)
        )

        if self.algorithm.trading_threshold >= residual >= -self.algorithm.trading_threshold:
            return

        base_trade_value = Value('1000')

        should_short_long_asset = self.algorithm.trading_threshold < residual
        pf = self.algorithm.pricing_factor
        long_pair_price = long_price * (pf if should_short_long_asset else 1 / pf)
        short_pair_price = short_price * (1 / pf if should_short_long_asset else pf)
        long_amount = base_trade_value / long_pair_price
        short_amount = (base_trade_value / short_pair_price) * regression.beta
        wait_until = timestamp + self.algorithm.wait_period

        if should_short_long_asset:
            _, max_long_price = self.long_pair_oracle.get_timerange_min_and_max_prices(
                timestamp,
                wait_until,
            )
            did_long_trade_fill = max_long_price >= long_pair_price
            min_short_price, _ = self.short_pair_oracle.get_timerange_min_and_max_prices(
                timestamp,
                wait_until,
            )
            did_short_trade_fill = min_short_price <= short_pair_price
        else:
            min_long_price, _ = self.long_pair_oracle.get_timerange_min_and_max_prices(
                timestamp,
                wait_until,
            )
            did_long_trade_fill = min_long_price <= long_pair_price
            _, max_short_price = self.short_pair_oracle.get_timerange_min_and_max_prices(
                timestamp,
                wait_until,
            )
            did_short_trade_fill = max_short_price >= short_pair_price

        added_long_asset_amount = Amount(0)
        added_short_asset_amount = Amount(0)
        added_quote_asset_amount = Amount(0)
        if did_long_trade_fill:
            sign = -1 if should_short_long_asset else 1
            added_long_asset_amount += sign * long_amount
            added_quote_asset_amount += Amount((-sign * long_amount * long_price).as_decimal())

        if did_short_trade_fill:
            sign = 1 if should_short_long_asset else -1
            added_short_asset_amount += sign * short_amount
            added_quote_asset_amount += Amount((-sign * short_amount * short_price).as_decimal())

        db.add(
            ResultEntity(
                **Result(
                    timestamp,
                    regression,
                    regression_detail,
                    did_short_trade_fill,
                    did_long_trade_fill,
                    added_long_asset_amount,
                    added_short_asset_amount,
                    added_quote_asset_amount,
                ).as_entity_kwargs(self.algorithm_id)
            )
        )
        db.commit()

    def _get_regression(self, from_timestamp, to_timestamp) -> tuple[Regression, RegressionDetail]:
        return get_linear_regression(
            self.long_pair_oracle.get_timerange_prices(from_timestamp, to_timestamp),
            self.short_pair_oracle.get_timerange_prices(from_timestamp, to_timestamp),
        )
