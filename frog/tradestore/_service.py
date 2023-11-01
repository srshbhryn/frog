from datetime import datetime, timedelta

import pytz
from django.db import models

from frog.square.rpc import RpcCode, RpcError, RpcService
from frog.types import Pair, Price

from django.db import models
from ._django_setup import setup


class Errors:
    class PriceIsNotAvailable(RpcError):
        def __init__(self) -> None:
            super().__init__(RpcCode.NOT_AVAILABLE)


class Service(RpcService):
    topic = b'prices'

    def __init__(self, *args, **kwargs) -> None:
        self.trade_model: models.Model = None
        super().__init__(*args, **kwargs)

    def run_server(self) -> None:
        setup()
        from .db.models import Trade
        self.trade_model = Trade
        return super().run_server()

    @RpcService.register
    def get(self, pair: Pair, timestamp: datetime) -> Price:
        price = (
            self.trade_model.objects.filter(
                pair=str(pair),
                time__lt=timestamp.timestamp(),
                time__gt=(timestamp - timedelta(seconds=60)).timestamp(),
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
            raise Errors.PriceIsNotAvailable
        return Price(price)

    @RpcService.register
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
                second=models.functions.Cast(60 * models.F('time'), models.IntegerField()) / 60,
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

        return {datetime.fromtimestamp(s + 1, tz=pytz.UTC): Price(d) for s, d in prices}
