import datetime
import functools

from frog.types import Asset, Amount, Value, Price, Pair, Regression
from tadpoles.prices import Oracle
from tadpoles.types import Exchange

from .types import Algorithm, Result


from .db import AlgorithmEntity, db

class PairTradingSimulation:
    def __init__(
        self,
        algorithm: Algorithm,
        start_at: datetime.datetime,
        end_at: datetime.datetime,
    ) -> None:
        self.start_at = start_at
        self.end_at = end_at
        self.algorithm = algorithm
        self.asset_to_pair_price_oracle_map = {
            self.algorithm.long_asset: Oracle(
                Exchange.NOBITEX,
                Pair(self.algorithm.long_asset, self.algorithm.quote_asset),
            ),
            self.algorithm.short_asset: Oracle(
                Exchange.NOBITEX,
                Pair(self.algorithm.short_asset, self.algorithm.quote_asset),
            ),
        }
        self.simulation_timestamp = start_at.timestamp()

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

    def get_time_range_min_and_max_prices(
        self,
        asset: Asset,
        from_timestamp: int,
        to_timestamp: int,
    ) -> tuple[Price, Price]:
        oracle = self.asset_to_pair_price_oracle_map[asset]

    def get_prices(self):
        pass

    def run_for(timestamp: datetime.datetime) -> None:
        pass
