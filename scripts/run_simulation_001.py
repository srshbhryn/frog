import datetime
import dataclasses
import enum

import tqdm

from frog.types import Asset
from tadpoles.types import Exchange
from tadpoles.prices.utils import get_candles, get_min_max_timestamps


EXCHANGE = Exchange.WALLEX
BASE_ASSET = Asset.USDT
QUOTE_ASSET = Asset.RLS


class Core:
    @dataclasses.dataclass
    class Order:
        created_at: int
        is_buy: bool
        price: float
        amount: float
        is_filled: bool
        is_cancelled: bool

        @property
        def is_sell(self):
            return not self.is_buy

    class StatKey(enum.Enum):
        FILLED_BUY = 0
        FILLED_SELL = 1
        CANCELED_BUY = 2
        CANCELED_SELL = 3

    def __init__(
        self,
        base: float,
        quote: float,
        order_gain: float,
        fee: float,
        trading_amount: float,
        look_back_len: int,
        wait_len: int,
    ):
        self.initial_base = base
        self.initial_quote = quote
        self.free_base = base
        self.blocked_base = 0
        self.free_quote = quote
        self.blocked_quote = 0
        self.order_gain = order_gain
        self.fee_factor = 1 - fee
        self.last_order_id = -1
        self.orders: dict[int, Core.Order] = {}
        self.trading_amount = trading_amount
        self.look_back_len = look_back_len
        self.wait_len = wait_len
        self.stats = {
            self.__class__.StatKey.CANCELED_BUY: 0,
            self.__class__.StatKey.CANCELED_SELL: 0,
            self.__class__.StatKey.FILLED_BUY: 0,
            self.__class__.StatKey.FILLED_SELL: 0,
        }
        self.ts_to_value_map: dict[int, float] = {}

    def run(self, timestamp: int):
        # we assume this function is begin called every minute
        self._check_for_filled_orders(timestamp)
        self._cancel_old_orders(timestamp)
        self._place_orders(timestamp)
        current_price = self.get_current_price(timestamp)
        self.ts_to_value_map[timestamp] = self.blocked_quote + self.free_quote + (self.blocked_base + self.free_base) * current_price

    def print_balances(self):
        print('\t'.join([str(v)
            for v in [
                self.free_base,
                self.blocked_base,
                self.free_quote,
                self.blocked_quote,
            ]
        ]))

    def get_current_price(self, timestamp: int):
        now_ts = datetime.datetime.fromtimestamp(timestamp)
        last_min_candles = get_candles(
            EXCHANGE,
            BASE_ASSET,
            QUOTE_ASSET,
            now_ts - datetime.timedelta(minutes=1),
            now_ts,
        )
        return last_min_candles.fixed_candles[-1].close_price

    def _check_for_filled_orders(self, timestamp: int):
        now_ts = datetime.datetime.fromtimestamp(timestamp)
        last_min_candles = get_candles(
            EXCHANGE,
            BASE_ASSET,
            QUOTE_ASSET,
            now_ts - datetime.timedelta(minutes=1),
            now_ts,
        )
        min_price = last_min_candles.fixed_candles[-1].min_price
        max_price = last_min_candles.fixed_candles[-1].max_price
        for order_id, order in self.orders.items():
            if order.is_cancelled:
                continue
            if order.is_filled:
                continue
            if order.is_buy and order.price < min_price:
                continue
            if order.is_sell and order.price > max_price:
                continue
            {
                True: self._make_buy_order_filled,
                False: self._make_sell_order_filled,
            }[order.is_buy](order_id)

    def _make_buy_order_filled(self, order_id: int):
        assert self.orders[order_id].is_filled is False
        assert self.orders[order_id].is_cancelled is False
        self.orders[order_id].is_filled = True
        order = self.orders[order_id]
        self.free_base += order.amount * self.fee_factor
        self.blocked_quote -= order.amount * order.price
        self.stats[self.__class__.StatKey.FILLED_BUY] += 1

    def _make_sell_order_filled(self, order_id: int):
        assert self.orders[order_id].is_filled is False
        assert self.orders[order_id].is_cancelled is False
        self.orders[order_id].is_filled = True
        order = self.orders[order_id]
        self.free_quote += order.amount * order.price * self.fee_factor
        self.blocked_base -= order.amount
        self.stats[self.__class__.StatKey.FILLED_SELL] += 1

    def _place_a_order(self, ts: int,  price, amount, is_buy):
        if int(ts / 60) % 10 != 0:
            return
        self.last_order_id += 1
        self.orders[self.last_order_id] = self.__class__.Order(
            ts,
            is_buy,
            price,
            amount,
            False,
            False,
        )
        if is_buy:
            quote = price * amount
            self.free_quote -= quote
            self.blocked_quote += quote
        else:
            self.free_base -= amount
            self.blocked_base += amount

    def _cancel_order(self, order_id):
        assert self.orders[order_id].is_filled is False
        assert self.orders[order_id].is_cancelled is False
        self.orders[order_id].is_cancelled = True
        if self.orders[order_id].is_buy:
            quote = self.orders[order_id].price * self.orders[order_id].amount
            self.free_quote += quote
            self.blocked_quote -= quote
            self.stats[self.__class__.StatKey.CANCELED_BUY] += 1
        else:
            base = self.orders[order_id].amount
            self.free_base += base
            self.blocked_base -= base
            self.stats[self.__class__.StatKey.CANCELED_SELL] += 1


    def _cancel_old_orders(self, timestamp: int):
        for order_id, order in self.orders.items():
            if not order.is_cancelled and not order.is_filled and timestamp - order.created_at > self.wait_len * 60:
                self._cancel_order(order_id)

    def _place_orders(self, timestamp: int):
        recent_candles = get_candles(
            EXCHANGE,
            BASE_ASSET,
            QUOTE_ASSET,
            datetime.datetime.fromtimestamp(timestamp - self.look_back_len * 60),
            datetime.datetime.fromtimestamp(timestamp),
        ).fixed_candles
        min_price = recent_candles[0].close_price
        max_price = recent_candles[0].close_price
        for candle in recent_candles:
            min_price = min(min_price, candle.close_price)
            max_price = max(max_price, candle.close_price)
        center_price = min_price + max_price
        center_price /= 2
        self._place_a_order(timestamp, center_price * self.order_gain, self.trading_amount, False)
        self._place_a_order(timestamp, center_price / self.order_gain, self.trading_amount, True)

    def get_base_delta(self):
        return self.blocked_base + self.free_base - self.initial_base

    def get_base_gain(self):
        return (self.blocked_base + self.free_base - self.initial_base) / self.initial_base

    def get_quote_delta(self):
        return self.blocked_quote + self.free_quote - self.initial_quote

    def get_quote_gain(self):
        return (self.blocked_quote + self.free_quote - self.initial_quote) / self.initial_quote

    def print_stats(self):
        for key in self.__class__.StatKey:
            print(f'{key.name}\t{self.stats[key]}')


def main():
    for x in range(20):
        min_ts, max_ts = get_min_max_timestamps(EXCHANGE, BASE_ASSET, QUOTE_ASSET)
        min_ts += 60 * 24 * 10 * x
        # min_ts += 60* 24 * 26
        # min_ts = max_ts - 60 * 24 * 200


        core = Core(
            base=1000,
            quote=50_000_000,
            order_gain=1.003,
            fee=.001,
            trading_amount=10,
            look_back_len=10,
            wait_len=10,
        )
        for i in  tqdm.tqdm(range(60 * 24 * 5)):
            core.run(min_ts + 60 * i)
        core.print_stats()
        print('\t'.join([f'{v:.2f}' for v in [core.blocked_base, core.free_base, core.blocked_base + core.free_base]]))
        print('\t'.join([f'{v:.2f}' for v in [core.blocked_quote, core.free_quote, core.blocked_quote + core.free_quote]]))
        print(min_ts, core.ts_to_value_map[min_ts] / 1000_000)
        print(min_ts + 60 * i, core.ts_to_value_map[min_ts + 60 * i] / 1000_000)
        print(core.get_base_gain())
        print(core.get_quote_gain())
    print('-----------------')
if __name__ == '__main__':
    main()
