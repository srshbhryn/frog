import asyncio
import dataclasses
import json
import logging

import zmq
import zmq.asyncio
from tornado import ioloop
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPResponse

from frog import config
from frog.bookwatch._helpers import translate_asset_name
from frog.config import ALL_PAIRS


@dataclasses.dataclass(slots=True)
class Trade:
    pair: str
    time: int
    amount: str
    price: str
    is_buyer_maker: bool

    def __hash__(self) -> int:
        return hash(f'{self.pair}{self.time}{self.amount}{self.price}{self.is_buyer_maker}')

    def as_dict(self):
        return {
            'pair': str(self.pair),
            'time': self.time,
            'amount': self.amount,
            'price': self.price,
            'is_buyer_maker': self.is_buyer_maker,
        }


class TradeStore:
    def __init__(self) -> None:
        self.surely_sent_time = -1
        self.time_to_sent_trades_hashes_map: dict[int, set[int]] = dict()

    def is_already_sent(self, trade: Trade) -> bool:
        if trade.time < self.surely_sent_time:
            self.post_process(trade.time)
            return True
        trade_hash = hash(trade)
        timestamp = trade.time
        ts_set = self.time_to_sent_trades_hashes_map.get(timestamp, set())
        if trade_hash in ts_set:
            self.post_process(timestamp)
            return True
        self.add_trade(timestamp, trade_hash)
        return False

    def add_trade(self, timestamp: int, trade_hash: int):
        if timestamp not in self.time_to_sent_trades_hashes_map:
            self.time_to_sent_trades_hashes_map[timestamp] = set()
        self.time_to_sent_trades_hashes_map[timestamp].add(trade_hash)
        self.post_process(timestamp)


    def post_process(self, timestamp):
        if self.surely_sent_time < timestamp - 1200_1000:
            self.surely_sent_time = timestamp - 1200_1000
        for ts in [ts for ts in self.time_to_sent_trades_hashes_map if ts < self.surely_sent_time]:
            self.time_to_sent_trades_hashes_map.pop(ts, None)


class NobitexTradeCollector:

    def __init__(self):
        self.client = AsyncHTTPClient()
        self.requests = {
            pair: HTTPRequest(f'https://api.nobitex.ir/v2/trades/{translate_asset_name(pair)}')
            for pair in ALL_PAIRS
        }
        ctx = zmq.asyncio.Context()
        self.zmq_sock = ctx.socket(zmq.PUB)
        self.zmq_sock.connect(config.HIGHWAY_XSUB_URI)
        self.store = TradeStore()

    async def run(self):
        while True:
            try:
                for pair in ALL_PAIRS:
                    ioloop.IOLoop.current().add_callback(self.fetch_market, pair=pair)
            except Exception:
                logging.exception('Error in nobitex trade collector')
            await asyncio.sleep(3)

    async def fetch_market(self, pair):
        response = await self.client.fetch(
            self.requests[pair],
            raise_error=False,
        )
        for trade in json.loads(response.body).get('trades', []):
            serialized_trade = self._serialize_trade(trade, pair)
            if not self.store.is_already_sent(serialized_trade):
                await self.zmq_sock.send_multipart(
                    [
                        f'trade_{pair}'.lower().encode(),
                        json.dumps(trade.as_dict()).encode(),
                    ],
                )

    def _serialize_trade(self, obj, pair):
        price_parts = str(obj['price']).split('.')
        is_buyer_maker = obj['type'] == 'sell'
        if len(price_parts) == 1:
            price_parts += ['0']
        if len(price_parts[0]) < 10:
            price_parts[0] = price_parts[0] + (10 - len(price_parts[0])) * '0'
        if len(price_parts[1]) < 10:
            price_parts[1] = (10 - len(price_parts[1])) * '0' + price_parts[1]
        return Trade(
            pair,
            obj['time'],
            str(obj['volume']),
            str(obj['price']),
            is_buyer_maker,
        )
