from datetime import datetime

from frog import config
from frog.types import Pair, Regression
from frog.utils.rpc import ZmqRpc

from ._ptreg import get_linear_regression


class Service(ZmqRpc):
    uri = config.ANALYSISSERVICE_URI
    bind_uri = config.ANALYSISSERVICE_BIND_URI

    @ZmqRpc.register
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


class Client(Service):
    is_client = True
