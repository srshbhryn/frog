import logging
import json
import typing
import zmq

from frog import config
from frog.utils import msgpack
from frog.utils.shortcuts import get_zmq_context
from frog.types import Pair, Value, Asset, Price
from frog.bookwatch.types import Book


from frog.ordermanager.types import Account


def main():
    subscribe_socket: zmq.Socket = get_zmq_context().socket(zmq.SUB)
    subscribe_socket.subscribe('oms_account_')
    subscribe_socket.subscribe('order_')
    subscribe_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')
    pair_to_price_map: dict[Pair, Price] = {}

    while True:
        try:
            topic_data, data = subscribe_socket.recv_multipart()
            topic = topic_data.decode()
            if 'order_' in topic:
                pair = Pair.get_from_str(topic.replace('order_', ''))
                book: Book = msgpack.loads(data)
                price = (book.asks[0].price + book.bids[0].price) / 2
                pair_to_price_map[pair] = price

            oms_name = topic.replace('oms_account_', '')
            account: Account = msgpack.loads(data)
            usdt_value = Value(0)
            rls_value = Value(0)
            for asset, balance in account.asset_to_balance_map.items():
                usdt_price = get_price(pair_to_price_map, asset, Asset.USDT)
                rls_price = get_price(pair_to_price_map, asset, Asset.RLS)
                if usdt_price is None or rls_price is None:
                    raise ValueError
                usdt_value += balance * usdt_price
                rls_value += balance * rls_price
            logging.info(
                json.dumps(
                    {
                        'oms': oms_name,
                        'account': account.account_id,
                        'usdt_value': str(usdt_value),
                        'rls_value': str(rls_value),
                    }
                )
            )

        except:
            logging.exception('Error in guardian.')


def get_price(
    pair_to_price_map: dict[Pair, Price],
    base: Asset,
    quote: Asset,
) -> typing.Optional[Price]:
    if quote == Asset.RLS:
        if base == Asset.RLS:
            return Price(1)

    if quote == Asset.USDT:
        if base == Asset.USDT:
            return Price(1)
        if base == Asset.RLS:
            usdt_price = pair_to_price_map.get(Pair(Asset.USDT, Asset.RLS))
            if usdt_price is None:
                return None
            return Price(1 / usdt_price.as_decimal())

    return pair_to_price_map.get(Pair(base, quote))
