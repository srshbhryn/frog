import dataclasses
import datetime
import enum
import functools
import logging
import time

import pytz

from frog.analyst import rpc as analyst_rpc
from frog.cores.eye._main import Context, Event
from frog.ordermanager.nobitex import rpc as nobitex_rpc
from frog.ordermanager.types import OrderStatus
from frog.tradestore import rpc as tradestore_rpc
from frog.types import Amount, Asset, Pair, Price, Side
from frog.utils import listener
from frog.utils.shortcuts import now


class State(enum.Enum):
    NO_OPEN_ORDER = 0
    OPEN_ORDER = 1


class Event(Exception):
    pass


class Action:
    def __call__(self, _: 'Context') -> list[Event]:
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
        return self.action(context)

@dataclasses.dataclass(slots=True)
class Context:
    state: State
    internal_events: list['Event']
    is_long_asset_position_long = False
    order_manager = analyst_rpc.Client()
    analyst = analyst_rpc.Client()
    trade_store = tradestore_rpc.Client()
    nobitex_client = nobitex_rpc.Client()
    open_order_ids: dict[tuple[Pair, Side], int]
    open_order_deadlines: dict[tuple[Pair, Side], datetime.datetime]
    regression_len = 120
    trade_threshold = 0.002
    pricing_factor = 1.0
    wait_period = datetime.timedelta(minutes=240)
    long_asset = Asset.BTC
    short_asset = Asset.ETH
    quote_asset = Asset.RLS
    base_trade_value = Amount('500_000_0')
    external_events_topic: type[listener.Topic]

    def __init__(self) -> None:
        self.internal_events = []
        self.open_order_ids = {}
        self.open_order_deadlines = {}

        class Topic(enum.Enum):
            LONG_ORDERBOOK = listener.Topic(f'order_{self.long_pair}'.encode())
            SHORT_ORDERBOOK = listener.Topic(f'order_{self.short_pair}'.encode())

        self.external_events_topic = Topic
        self.event_listener = listener.Listener(list(self.event_listener_topics))

    @property
    def long_pair(self) -> Pair:
        return Pair(self.long_asset, self.quote_asset)

    @property
    def short_pair(self) -> Pair:
        return Pair(self.short_asset, self.quote_asset)

    @functools.cached_property
    def event_listener_topics(self) -> type[enum.Enum]:
        return self.external_events_topic

    @functools.cached_property
    def event_listener(self) -> listener.Listener:
        return listener.Listener(list(self.event_listener_topics))


class SleepForAWhile(Action):
    def __init__(self, a_while: int) -> None:
        super().__init__()
        self.a_while = a_while

    def __call__(self, _: Context) -> list[Event]:
        time.sleep(self.a_while)
        return []


class PlaceOrder(Action):
    def __init__(self, pair: Pair, amount: Amount, price: Price, side: Side) -> None:
        self.pair = pair
        self.amount = amount
        self.price = price
        self.side = side
        super().__init__()

    def __call__(self, context: Context) -> list[Event]:
        order_id = context.nobitex_client.place_order(
            nobitex_rpc.Order(
                pair=self.pair,
                side=self.side,
                price=self.price,
            ),
        )
        context.open_order_ids[(self.pair, self.side)] = order_id
        context.open_order_deadlines[
            (
                self.pair,
                self.side,
            )
        ] = (
            now() + context.wait_period
        )
        return []


class CancelExpiredOrders(Action):
    def __call__(self, context: Context) -> list[Event]:
        orders_keys = list(context.open_order_ids.keys())
        for orders_key in orders_keys:
            if now() > context.open_order_deadlines[orders_key]:
                try:
                    context.nobitex_client.cancel_order(context.open_order_ids[orders_key])
                    context.open_order_ids.pop(orders_key, None)
                    context.open_order_deadlines.pop(orders_key, None)

                except nobitex_rpc.Client.Err:
                    logging.exception('err in CancelExpiredOrders')
        return []


class CheckIfOrdersAreOpen(Action):
    def __call__(self, context: Context) -> list[Event]:
        try:
            for k, order_id in [(k, oid) for k, oid in context.open_order_ids.items()]:
                if context.nobitex_client.get_order(order_id).status in (
                    OrderStatus.filled,
                    OrderStatus.canceled,
                ):
                    context.open_order_ids.pop(k, None)
                else:
                    break

        except nobitex_rpc.Client.Err:
            logging.exception('err in CheckIfOrdersAreFilled')
        else:
            if not context.open_order_ids:
                return [ShouldDo(ChangeState(State.NO_OPEN_ORDER))]
            return [
                ShouldDo(SleepForAWhile(30)),
                ShouldDo(CancelExpiredOrders()),
                ShouldDo(CheckIfOrdersAreOpen()),
            ]


class CheckResidual(Action):
    def __call__(self, context: Context) -> list[Event]:
        end_time = now().replace(second=0, microsecond=0)
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
            case _, ShouldDo():
                fun = event.do

            case State.NO_OPEN_ORDER, topics.LONG_ORDERBOOK | topics.SHORT_ORDERBOOK:
                fun = CheckResidual()

            case State.OPEN_ORDER, _:
                fun = CheckIfOrdersAreOpen()

            case _:
                logging.error(
                    'Unhandled "(state, event)"  pair: %s %s',
                    event,
                    context.state,
                )

                def fun() -> list[Event]:
                    return []

        context.internal_events += fun(context)
