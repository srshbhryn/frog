
from django.db import models


class Trade(models.Model):
    pair = models.CharField(max_length=10)
    time = models.FloatField()
    amount = models.DecimalField(max_digits=32, decimal_places=16)
    price = models.DecimalField(max_digits=32, decimal_places=16)
    is_buyer_maker = models.BooleanField()

    class Meta:
        indexes = (
            models.Index(fields=('pair', 'time')),
        )
