
from frog import config
from frog.utils.rpc import ZmqRpc

from ._ptreg import get_residual


class AnalysisService(ZmqRpc):
    uri = config.ANALYSISSERVICE_URI
    bind_uri = config.ANALYSISSERVICE_BIND_URI

    @ZmqRpc.register
    def get_residual(
        self,
        long_symbol,
        short_symbol,
        start_time,
        end_time,
        current_long_price,
        current_short_price,
    ):
        return get_residual(
            long_symbol,
            short_symbol,
            start_time,
            end_time,
            current_long_price,
            current_short_price,
        )


class AnalysisClient(ZmqRpc):
    is_client = True
