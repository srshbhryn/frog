import dataclasses
import datetime
import enum
import functools
import logging
import time

from frog.analyst import rpc as analyst_rpc
from frog.ordermanager.nobitex import rpc as nobitex_rpc
from frog.ordermanager.types import OrderStatus
from frog.tradestore import rpc as tradestore_rpc
from frog.types import Amount, Asset, Pair, Price, Side
from frog.utils import listener
from frog.square.rpc import RpcClient, RpcService
from frog.utils.listener import Event
from frog.utils.shortcuts import now


class State(enum.Enum):
    NO_OPEN_ORDER = 0
    OPEN_ORDER = 1


class Action:
    def __call__(self, _: 'Context') -> None:
        raise NotImplementedError


class ChangeState(Action):
    def __init__(self, state: State) -> None:
        self._state = state

    def __call__(self, context: 'Context') -> None:
        context.state = self._state


class ShouldDo(listener.Reminder):
    def __init__(
        self,
        context: 'Context',
        timeout: datetime.timedelta,
        actions: list[Action],
    ) -> None:
        self.actions = actions
        context.event_listener.add_reminder(timeout, self)

    def do(self, context: 'Context') -> None:
        for action in self.actions:
            action(context)


@dataclasses.dataclass(slots=True)
class Topics:
    LONG_ORDERBOOK: listener.Topic
    SHORT_ORDERBOOK: listener.Topic


class Client(RpcClient):
    analyst = analyst_rpc.Service()
    trade_store = tradestore_rpc.Service()
    nobitex_client = nobitex_rpc.Service()


@dataclasses.dataclass(slots=True)
class Context:
    state: State
    is_long_asset_position_long = False
    client = Client()
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
    external_events_topics: Topics
    action_queue: list[Action]
    event_listener: listener.Listener

    @property
    def analyst(self) -> RpcService:
        return self.client.analyst

    @property
    def trade_store(self) -> RpcService:
        return self.client.trade_store

    @property
    def nobitex_client(self) -> RpcService:
        return self.client.nobitex_client

    def __init__(self) -> None:
        self.open_order_ids = {}
        self.open_order_deadlines = {}
        self.external_events_topics = Topics(
            listener.Topic(f'order_{self.long_pair}'.encode()),
            listener.Topic(f'order_{self.short_pair}'.encode()),
        )
        self.action_queue = []
        self.event_listener = listener.Listener(
            [
                self.external_events_topics.LONG_ORDERBOOK,
                self.external_events_topics.SHORT_ORDERBOOK,
            ],
        )

    def add_action(self, action: Action) -> None:
        self.action_queue.append(action)

    def pop_action(self) -> Action:
        return self.action_queue.pop(0)

    def has_action(self) -> bool:
        return len(self.action_queue) != 0

    @property
    def long_pair(self) -> Pair:
        return Pair(self.long_asset, self.quote_asset)

    @property
    def short_pair(self) -> Pair:
        return Pair(self.short_asset, self.quote_asset)


class SleepForAWhile(Action):
    def __init__(self, a_while: int) -> None:
        super().__init__()
        self.a_while = a_while

    def __call__(self, _: Context) -> None:
        time.sleep(self.a_while)


class PlaceOrder(Action):
    def __init__(self, pair: Pair, amount: Amount, price: Price, side: Side) -> None:
        self.pair = pair
        self.amount = amount
        self.price = price
        self.side = side
        super().__init__()

    def __call__(self, context: Context) -> None:
        order_id = context.nobitex_client.place_order(
            nobitex_rpc.Order(
                amount=self.amount,
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


class CancelExpiredOrders(Action):
    def __call__(self, context: Context) -> None:
        orders_keys = list(context.open_order_ids.keys())
        for orders_key in orders_keys:
            if now() > context.open_order_deadlines[orders_key]:
                try:
                    context.nobitex_client.cancel_order(context.open_order_ids[orders_key])
                    context.open_order_ids.pop(orders_key, None)
                    context.open_order_deadlines.pop(orders_key, None)

                except nobitex_rpc.Client.Err:
                    logging.exception('err in CancelExpiredOrders')


class CheckIfOrdersAreOpen(Action):
    def __call__(self, context: Context) -> None:
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
                context.add_action(ChangeState(State.NO_OPEN_ORDER))

            else:
                for action in (
                    SleepForAWhile(30),
                    CancelExpiredOrders(),
                    CheckIfOrdersAreOpen(),
                ):
                    context.add_action(action)


class CheckResidual(Action):
    def __call__(self, context: Context) -> None:
        end_time = now().replace(second=0, microsecond=0)
        start_time = end_time - datetime.timedelta(minutes=context.regression_len)

        try:
            long_price = context.trade_store.get(context.long_pair, end_time)
            short_price = context.trade_store.get(context.short_pair, end_time)
        except tradestore_rpc.Errors.PriceIsNotAvailable:
            logging.exception('PriceIsNotAvailable')
            return

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
            actions = [
                PlaceOrder(
                    context.long_pair,
                    context.base_trade_value,
                    long_price * context.pricing_factor,
                    Side.SHORT,
                ),
                PlaceOrder(
                    context.short_pair,
                    context.base_trade_value * regression.beta,
                    short_price / context.pricing_factor,
                    Side.LONG,
                ),
            ]
        elif residual < 1 - context.trade_threshold:
            actions = [
                PlaceOrder(
                    context.long_pair,
                    context.base_trade_value,
                    long_price / context.pricing_factor,
                    Side.LONG,
                ),
                PlaceOrder(
                    context.short_pair,
                    context.base_trade_value * regression.beta,
                    short_price * context.pricing_factor,
                    Side.SHORT,
                ),
            ]
        else:
            actions = []

        for action in actions:
            context.add_action(action)


def main() -> None:
    context = Context()
    topics = context.external_events_topics

    while True:
        logging.debug('main loop')
        if context.has_action():
            logging.debug('has action')
            context.pop_action()(context)
            continue

        logging.debug('waiting for event')
        event = context.event_listener.wait()
        logging.debug('received')

        if isinstance(event, ShouldDo):
            event.do(context)
        elif context.state == State.NO_OPEN_ORDER and event in (
            topics.LONG_ORDERBOOK,
            topics.SHORT_ORDERBOOK,
        ):
            CheckResidual()(context)
        elif context.state == State.OPEN_ORDER:
            CheckIfOrdersAreOpen()(context)
        else:
            logging.error(
                'Unhandled "(state, event)"  pair: %s %s',
                event,
                context.state,
            )
