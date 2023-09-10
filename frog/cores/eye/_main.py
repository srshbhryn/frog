import dataclasses
import datetime
import enum
import functools
import logging
import time

import pytz

from frog.analyst import rpc as analyst_rpc
from frog.tradestore import rpc as tradestore_rpc
from frog.ordermanager.nobitex import rpc as nobitex_rpc
from frog.types import Amount, Asset, Pair, Price, Side
from frog.utils import listener


class State(enum.Enum):
    NO_OPEN_ORDER = 0
    ONE_OPEN_ORDER = 1
    TWO_OPEN_ORDERs = 2


class Event(Exception):
    pass


class FailedOrderPlacement(Event):
    pass


class Action:
    def __call__(self, context: 'Context') -> list[Event]:
        raise NotImplementedError


class ChangeState(Action):
    def __init__(self, state: State) -> None:
        self._state = state

    def __call__(self, context: 'Context') -> list[Event]:
        context.state = self._state
        return []


class ShouldDo(Event):
    def __init__(self, action: Action) -> None:
        super().__init__()
        self.action = action

    def do(self, context: 'Context') -> list[Event]:
        self.action(context)


class CancelAllOrders(Action):
    def __call__(self, context: 'Context') -> list[Event]:
        return []


@dataclasses.dataclass(slots=True)
class Context:
    state: State
    internal_events: list['Event']
    is_long_asset_position_long = False
    order_manager = analyst_rpc.Client()
    analyst = analyst_rpc.Client()
    trade_store = tradestore_rpc.Client()
    regression_len = 120
    trade_threshold = 0.002
    pricing_factor = 1.0
    wait_period = 240
    long_asset = Asset.BTC
    short_asset = Asset.ETH
    quote_asset = Asset.RLS
    base_trade_value = Amount('300_000_0')

    def __init__(self) -> None:
        self.event_listener = listener.Listener(list(self.event_listener_topics))
        self.internal_events = []

    @property
    def long_pair(self) -> Pair:
        return Pair(self.long_asset, self.quote_asset)

    @property
    def short_pair(self) -> Pair:
        return Pair(self.short_asset, self.quote_asset)

    @functools.cached_property
    def event_listener_topics(self) -> enum.Enum:
        class Topic(enum.Enum):
            MY_ORDER_FILL = listener.Topic(b'my_trade_')
            LONG_PAIR_ORDERBOOK = listener.Topic(f'order_{self.long_pair}'.encode())
            SHORT_PAIR_ORDERBOOK = listener.Topic(f'order_{self.short_pair}'.encode())

        return Topic

    @functools.cached_property
    def event_listener(self) -> listener.Listener:
        return listener.Listener(list(self.event_listener_topics))


class SleepForAWhile(Action):
    def __init__(self, a_while: int) -> None:
        super().__init__()
        self.a_while = a_while


class PlaceOrder(Action):
    def __init__(self, pair: Pair, amount: Amount, price: Price, side: Side) -> None:
        self.pair = pair
        self.amount = amount
        self.price = price
        super().__init__()

    def __call__(self, context: Context) -> list[Event]:
        return []


class CheckResidual(Action):
    def __call__(self, context: Context) -> list[Event]:
        end_time = datetime.datetime.fromtimestamp(
            int(time.time() / 60) * 60,
            tz=pytz.UTC,
        )
        start_time = end_time - datetime.timedelta(minutes=context.regression_len)
        try:
            long_price = context.trade_store.get(context.long_pair, end_time)
            short_price = context.trade_store.get(context.short_pair, end_time)
        except tradestore_rpc.Errors.PriceIsNotAvailable:
            events = []
        else:
            regression = context.analyst.get_regression(
                context.long_pair,
                context.short_pair,
                start_time,
                end_time,
            )
            residual = (
                long_price / regression.long_price_normalizer
                - regression.alpha
                - regression.beta * short_price / regression.short_price_normalizer
            )

            if residual > 1 + context.trade_threshold:
                events = [
                    ShouldDo(
                        PlaceOrder(
                            context.long_pair,
                            context.base_trade_value,
                            long_price * context.pricing_factor,
                            Side.SHORT,
                        ),
                    ),
                    ShouldDo(
                        PlaceOrder(
                            context.short_pair,
                            context.base_trade_value * regression.beta,
                            short_price / context.pricing_factor,
                            Side.LONG,
                        ),
                    ),
                ]
            elif residual < 1 - context.trade_threshold:
                events = [
                    ShouldDo(
                        PlaceOrder(
                            context.long_pair,
                            context.base_trade_value,
                            long_price / context.pricing_factor,
                            Side.LONG,
                        ),
                    ),
                    ShouldDo(
                        PlaceOrder(
                            context.short_pair,
                            context.base_trade_value * regression.beta,
                            short_price * context.pricing_factor,
                            Side.SHORT,
                        ),
                    ),
                ]
            else:
                events = []

        return events


def main(context: Context) -> None:
    topics = context.event_listener_topics
    while True:
        if context.internal_events:
            event = context.internal_events.pop()
        else:
            event = context.event_listener.wait()

        match context.state, event:
            case State.NO_OPEN_ORDER, (topics.LONG_PAIR_ORDERBOOK | topics.SHORT_PAIR_ORDERBOOK):
                fun = CheckResidual()

            case State.ONE_OPEN_ORDER, topics.MY_ORDER_FILL:
                fun = ChangeState(State.NO_OPEN_ORDER)

            case _, ShouldDo():
                fun = event.do

            case _:
                logging.error('Unhandled event state pair: %s %s', event, context.state)

                def fun() -> list[Event]:
                    return []

        context.internal_events += fun(context)
