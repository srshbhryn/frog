from datetime import datetime, timedelta

from django.db import models

from frog import config
from frog.types import Pair, Price
from frog.utils.rpc import RpcError, ZmqRpc

from ._django_setup import setup


class Errors:
    class PriceIsNotAvailable(RpcError):
        def __init__(self) -> None:
            super().__init__(RpcError.Code.NOT_AVAILABLE)


class Service(ZmqRpc):
    uri = config.PRICESERVICE_URI
    bind_uri = config.PRICESERVICE_BIND_URI

    def __init__(self) -> None:
        super().__init__()
        setup()
        from .db.models import Trade
        self.trade_model = Trade

    def get(self, pair: Pair, timestamp: datetime) -> Price:
        price = (
            self.trade_model.objects.filter(
                pair=str(pair),
                time__lt=timestamp.timestamp(),
                time__gt=(timestamp - timedelta(seconds=1)).timestamp(),
            )
            .aggregate(
                price=models.Sum(
                    models.F('amount') * models.F('price'),
                )
                / models.Sum(models.F('amount')),
            )
            .get('price')
        )
        if price is None:
            raise Errors.PriceIsNotAvailable()
        return Price(price)

    def get_timerange_price(
        self,
        pair: Pair,
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> dict[datetime, Price]:
        prices = (
            self.trade_model.objects.filter(
                pair=pair,
                time__gt=start_timestamp.timestamp(),
                time__lt=end_timestamp.timestamp(),
            )
            .annotate(
                second=models.functions.Cast('time', models.IntegerField()),
            )
            .values('second')
            .annotate(
                price=models.Sum(
                    models.F('amount') * models.F('price'),
                )
                / models.Sum(models.F('amount')),
            )
            .values_list('second', 'price')
        )

        return {datetime.fromtimestamp(s + 1): Price(d) for s, d in prices}


class Client(Service):
    is_client = True
