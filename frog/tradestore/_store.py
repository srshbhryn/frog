
import zmq

from frog import config
from frog.utils import msgpack
from frog.utils.shortcuts import get_zmq_context

from ._django_setup import migrate, setup


def store_trade(trade: dict) -> None:
    from .db.models import Trade
    trade['time'] = trade['time'] / 1000
    Trade.objects.create(**trade)


def store_main() -> None:
    setup()
    migrate()
    socket: zmq.Socket = get_zmq_context().socket(zmq.SUB)
    socket.subscribe('trade_')
    socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')

    while True:
        _, data = socket.recv_multipart()
        store_trade(msgpack.loads(data))
