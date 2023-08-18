from datetime import datetime
from decimal import Decimal

from frog import config
from frog.types import Asset, Price
from frog.utils.rpc import ZmqRpc

from ._ptreg import get_residual


class Service(ZmqRpc):
    uri = config.ANALYSISSERVICE_URI
    bind_uri = config.ANALYSISSERVICE_BIND_URI

    @ZmqRpc.register
    def get_residual(
        self,
        long_asset: Asset,
        short_asset: Asset,
        start_time: datetime,
        end_time: datetime,
        current_long_price: Price,
        current_short_price: Price,
    ) -> Decimal:
        return get_residual(
            long_asset,
            short_asset,
            start_time,
            end_time,
            current_long_price,
            current_short_price,
        )


class Client(Service):
    is_client = True
