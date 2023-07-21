import logging
import json
from datetime import datetime, timedelta

import zmq

from django.db import models

from frog import config

from ._django_setup import setup


class PriceService:
    def __init__(self) -> None:
        setup()
        from .db.models import Trade
        self.trade_model = Trade

    def get(self, pair: str, timestamp: float):
        price = self.trade_model.objects.filter(
            pair=pair,
            time__lt=timestamp,
            time__gt=timestamp - timedelta(seconds=1),
        ).aggregate(price=models.Sum(
            models.F('amount') * models.F('price')
        ) / models.Sum(models.F('amount'))).get('price')
        return price

    def get_timerange_price(self, pair: str, start_timestamp: float, end_timestamp: float):
        prices = self.trade_model.objects.filter(
            pair=pair,
            time__gt=start_timestamp,
            time__lt=end_timestamp,
        ).annotate(
            second=models.functions.Cast('time', models.IntegerField())
        ).values('second').annotate(price=models.Sum(
            models.F('amount') * models.F('price')
        ) / models.Sum(models.F('amount'))).values_list('second', 'price')
        logging.debug(prices.query)
        return dict([(s + 1, str(d)) for s, d in prices])


def service_main():
    contex = zmq.Context()
    socket = contex.socket(zmq.REP)
    socket.bind(config.PRICESERVICE_BIND_URI)
    price_service = PriceService()
    while True:
        request = socket.recv_multipart()
        subject = request[0].decode()
        if subject == 'p':
            pair = request[1].decode()
            timestamp = float(request[2].decode())
            price = price_service.get(pair, timestamp)
            if price is None:
                socket.send_multipart([b'4',])
            socket.send_multipart([b'0', str(price).encode()])
        elif subject == 'pr':
            pair = request[1].decode()
            start_timestamp = float(request[2].decode())
            end_timestamp = float(request[3].decode())
            prices = price_service.get_timerange_price(pair, start_timestamp, end_timestamp)
            if not prices:
                socket.send_multipart([b'4',])
            socket.send_multipart([b'0',  json.dumps(prices).encode()])
        else:
            socket.send_multipart([b'1'])
