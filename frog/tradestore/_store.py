
import zmq

from frog import config
from frog.utils import msgpack
from frog.utils.shortcuts import get_zmq_context
from frog.tradecollector import Trade as TradeDTO

from ._django_setup import migrate, setup


def store_trade(trade: TradeDTO) -> None:
    from .db.models import Trade

    Trade.objects.create(
        pair=trade.pair,
        time=trade.time / 1000,
        amount=trade.amount.as_decimal(),
        price=trade.price.as_decimal(),
        is_buyer_maker=trade.is_buyer_maker,
    )


def store_main() -> None:
    setup()
    migrate()
    socket: zmq.Socket = get_zmq_context().socket(zmq.SUB)
    socket.subscribe('trade_')
    socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')

    while True:
        _, data = socket.recv_multipart()
        store_trade(msgpack.loads(data))
