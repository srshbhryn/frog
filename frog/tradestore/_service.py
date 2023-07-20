import logging
from datetime import datetime, timedelta

import zmq


from django.db import models

from frog.config import Config

from ._django_setup import setup


class PriceService:
    def __init__(self) -> None:
        setup()
        from .db.models import Trade
        self.trade_model = Trade

    def get(self, pair: str, timestamp: int):
        timestamp = datetime.fromtimestamp(timestamp / 1000)
        price = self.trade_model.objects.filter(
            pair=pair,
            time__lt=timestamp + timedelta(seconds=1),
            time__gt=timestamp - timedelta(seconds=1),
        ).aggregate(price=models.Sum(
            models.F('amount') * models.F('price')
        ) / models.Sum(models.F('amount'))).get('price')
        return price


def service_main():
    contex = zmq.Context()
    socket = contex.socket(zmq.REP)
    socket.bind(f'tcp://*:{Config.priceservice_port}')
    price_service = PriceService()
    while True:
        request = socket.recv_multipart()
        subject = request[0].decode()
        if subject == 'p':
            pair = request[1].decode()
            timestamp = int(request[2].decode())
            price = price_service.get(pair, timestamp)
            if price is None:
                socket.send_multipart([b'4',])
            socket.send_multipart([b'0', str(price).encode()])
        else:
            socket.send_multipart([b'1'])
