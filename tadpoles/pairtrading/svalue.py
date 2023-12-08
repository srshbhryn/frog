import datetime
from decimal import Decimal
from typing import Optional

import numpy as np

from frog.types import Asset, Pair
from tadpoles.types import Exchange
from tadpoles.prices import Oracle


class SValueOracle:
    def __init__(self, index: Pair, target_pair: Pair) -> None:
        self.index_oracle = Oracle(Exchange.NOBITEX, index)
        self.target_oracle = Oracle(Exchange.NOBITEX, target_pair)
        self.alpha: Optional[Decimal] = None
        self.beta: Optional[Decimal] = None
        self.kappa: Optional[Decimal] = None
        self.m: Optional[Decimal] = None
        self.sigma: Optional[Decimal] = None

    def get_s_score(self, timestamp: datetime.datetime):
        pass
