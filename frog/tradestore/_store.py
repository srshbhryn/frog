import json

import zmq

from frog import config

from ._django_setup import migrate, setup


def store_trade(trade):
    from .db.models import Trade
    trade['time'] = trade['time'] / 1000
    Trade.objects.create(**trade)


def store_main():
    setup()
    migrate()
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.subscribe('trade_')
    socket.connect(config.HIGHWAY_XPUB_URI)
    while True:
        data = socket.recv_multipart()
        store_trade(json.loads(data[1]))
