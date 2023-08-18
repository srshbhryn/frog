from decimal import Decimal

from django.db import models


class Trade(models.Model):
    pair: models.CharField = models.CharField(max_length=10)
    time: models.FloatField = models.FloatField()
    amount: models.DecimalField = models.DecimalField(max_digits=32, decimal_places=16)
    price: models.DecimalField = models.DecimalField(max_digits=32, decimal_places=16)
    is_buyer_maker: models.BooleanField = models.BooleanField()

    class Meta:
        indexes = (
            models.Index(fields=('pair', 'time')),
        )
