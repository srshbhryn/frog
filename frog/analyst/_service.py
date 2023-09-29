from datetime import datetime

from frog.square.rpc import RpcService
from frog.types import Pair, Regression

from ._ptreg import get_linear_regression


class Service(RpcService):
    topic = b'ptreg'

    @RpcService.register
    def get_regression(
        self,
        long_pair: Pair,
        short_pair: Pair,
        start_time: datetime,
        end_time: datetime,
    ) -> Regression:
        return get_linear_regression(
            long_pair,
            short_pair,
            start_time,
            end_time,
        )
