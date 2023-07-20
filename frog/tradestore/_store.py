import json
from datetime import datetime

import zmq

from frog.config import Config
from ._django_setup import setup


def store_trade(trade):
    from .db.models import Trade
    trade['time'] = datetime.fromtimestamp(trade['time'] / 1000)
    Trade.objects.create(**trade)


def sotre_main():
    setup()
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.subscribe("")
    socket.connect(f'tcp://127.0.0.1:{Config.tradecollector_port}')
    while True:
        data = socket.recv_multipart()
        store_trade(json.loads(data[1]))
