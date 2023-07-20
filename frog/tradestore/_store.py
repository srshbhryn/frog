import json
from datetime import datetime

import zmq

from frog import config
from ._django_setup import setup, migrate


def store_trade(trade):
    from .db.models import Trade
    trade['time'] = datetime.fromtimestamp(trade['time'] / 1000)
    Trade.objects.create(**trade)


def sotre_main():
    setup()
    migrate()
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.subscribe("")
    socket.connect(config.TRADECOLLECTOR_URI)
    while True:
        data = socket.recv_multipart()
        store_trade(json.loads(data[1]))
