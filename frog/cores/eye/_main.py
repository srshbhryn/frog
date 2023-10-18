import asyncio
import dataclasses
import datetime
import enum
import logging
import time
from decimal import Decimal

from frog.analyst import rpc as analyst_rpc
from frog.cores.eye._main import Context
from frog.ordermanager.nobitex import rpc as nobitex_rpc
from frog.ordermanager.types import OrderStatus
from frog.square.rpc import RpcClient
from frog.tradestore import rpc as tradestore_rpc
from frog.types import Amount, Asset, Pair, Price, Side, Regression
from frog.utils import listener
from frog.utils.shortcuts import now


class AssetState(enum.Enum):
    NO_ORDER = 0
    OPEN_ORDER = 1


class State(enum.Enum):
    NN = (AssetState.NO_ORDER, AssetState.NO_ORDER)
    LN = (AssetState.OPEN_ORDER, AssetState.NO_ORDER)
    NS = (AssetState.NO_ORDER, AssetState.OPEN_ORDER)
    LS = (AssetState.OPEN_ORDER, AssetState.OPEN_ORDER)


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
        self.task = context.event_listener.add_reminder(timeout, self)

    def do(self, context: 'Context') -> None:
        for action in self.actions:
            action(context)


@dataclasses.dataclass(slots=True)
class Topics:
    LONG_ASSET_ORDERBOOK: listener.Topic
    SHORT_ASSET_ORDERBOOK: listener.Topic
    LONG_ASSET_FILL: listener.Topic
    SHORT_ASSET_FILL: listener.Topic

class Client(RpcClient):
    analyst = analyst_rpc.Service()
    trade_store = tradestore_rpc.Service()
    nobitex_client = nobitex_rpc.Service()


class CancelOrder(Action):
    def __init__(self, order: 'Order') -> None:
        self.order = order
        super().__init__()

    def __call__(self, context: Context) -> None:
        # call rpc
        if self.order.pair == context.long_pair:
            # context.state.value[0] =
            pass


@dataclasses.dataclass(slots=True)
class Order:
    context: Context
    pk: int
    pair: Pair
    side: Side
    amount: Amount
    price: Price
    filled_amount: Amount
    cancellation_task: asyncio.Task[None]

    @classmethod
    def new(
        cls,
        context: Context,
        listener: listener.Listener,
        pair: Pair,
        side: Side,
        amount: Amount,
        price: Price,
    ) -> 'Order':
        order = cls(
            context.nobitex_client.place_order(
                nobitex_rpc.Order(
                    amount=amount,
                    pair=pair,
                    side=side,
                    price=price,
                ),
            ),
            pair,
            side,
            amount,
            price,
            Decimal('0'),
            None,
        )
        order.cancellation_task = listener.add_reminder(
            context.wait_period,
            CancelOrder(order),
        )

    def update_fill(self, amount: Amount):
        self.filled_amount += amount
        if self.filled_amount == self.amount:
            self.cancellation_task.cancel()
            self.context.set_pair_order_to_close(self.pair)

class ActionQueue:
    def __init__(self) -> None:
        self._actions: list[Action] = []

    def add_action(self, action: Action) -> None:
        self._actions.append(action)

    def pop_action(self) -> Action:
        return self._actions.pop(0)

    def has_action(self) -> bool:
        return len(self._actions) != 0


@dataclasses.dataclass(slots=True)
class Context:
    state: State

    external_events_topics: Topics

    # helpers
    action_queue: ActionQueue
    event_listener: listener.Listener
    client: Client

    ####  config
    regression_len = 120
    trade_threshold = Decimal('0.002')
    pricing_factor = Decimal('1.0')
    wait_period = datetime.timedelta(minutes=240)
    long_asset = Asset.BTC
    short_asset = Asset.ETH
    quote_asset = Asset.RLS
    base_trade_value = Amount('500_000_0')

    @property
    def analyst(self) -> analyst_rpc.Service:
        return self.client.analyst

    @property
    def trade_store(self) -> tradestore_rpc.Service:
        return self.client.trade_store

    @property
    def nobitex_client(self) -> nobitex_rpc.Service:
        return self.client.nobitex_client

    def __init__(self) -> None:
        self.state = State.NO_OPEN_ORDER
        self.external_events_topics = Topics(
            listener.Topic(f'order_{self.long_pair}_LONG'.encode()),
            listener.Topic(f'order_{self.long_pair}_SHORT'.encode()),
            listener.Topic(f'order_{self.short_pair}_LONG'.encode()),
            listener.Topic(f'order_{self.short_pair}_SHORT'.encode()),
        )
        self.client = Client()
        self.action_queue = ActionQueue()
        self.event_listener = listener.Listener(
            [
                self.external_events_topics.LONG_LONG_ORDERBOOK,
                self.external_events_topics.LONG_SHORT_ORDERBOOK,
                self.external_events_topics.SHORT_LONG_ORDERBOOK,
                self.external_events_topics.SHORT_SHORT_ORDERBOOK,
            ],
        )

    @property
    def long_pair(self) -> Pair:
        return Pair(self.long_asset, self.quote_asset)

    @property
    def short_pair(self) -> Pair:
        return Pair(self.short_asset, self.quote_asset)

    def set_pair_order_to_close(self, pair: Pair) -> None:
        if pair == self.long_pair:
            if self.state == State.LN:
                self.state = State.NN

            elif self.state == State.LS:
                self.state = State.NS

        elif pair == self.long_pair:
            if self.state == State.NS:
                self.state = State.NN

            elif self.state == State.LS:
                self.state = State.LN

    def set_pair_order_to_open(self, pair: Pair) -> None:
        if pair == self.long_pair:
            if self.state == State.NN:
                self.state = State.LN

            elif self.state == State.NS:
                self.state = State.LS

        elif pair == self.long_pair:
            if self.state == State.NN:
                self.state = State.NS

            elif self.state == State.LN:
                self.state = State.LS

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
                context.action_queue.add_action(ChangeState(State.NO_OPEN_ORDER))

            else:
                for action in (
                    SleepForAWhile(30),
                    CancelExpiredOrders(),
                    CheckIfOrdersAreOpen(),
                ):
                    context.action_queue.add_action(action)


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

        regression: Regression = context.analyst.get_regression(
            context.long_pair,
            context.short_pair,
            start_time,
            end_time,
        )
        regression.alpha = Decimal(regression.alpha)
        regression.beta = Decimal(regression.beta)
        regression.long_price_normalizer = Decimal(regression.long_price_normalizer)
        regression.short_price_normalizer = Decimal(regression.short_price_normalizer)
        residual = (
            long_price / regression.long_price_normalizer
            - regression.alpha
            - regression.beta * short_price / regression.short_price_normalizer
        )

        if residual > 1 + context.trade_threshold:
            actions = [
                PlaceOrder(
                    context.long_pair,
                    context.base_trade_value / (long_price * context.pricing_factor),
                    long_price * context.pricing_factor,
                    Side.SHORT,
                ),
                PlaceOrder(
                    context.short_pair,
                    context.base_trade_value * regression.beta / (short_price / context.pricing_factor),
                    short_price / context.pricing_factor,
                    Side.LONG,
                ),
            ]
        elif residual < 1 - context.trade_threshold:
            actions = [
                PlaceOrder(
                    context.long_pair,
                    context.base_trade_value / (long_price / context.pricing_factor),
                    long_price / context.pricing_factor,
                    Side.LONG,
                ),
                PlaceOrder(
                    context.short_pair,
                    context.base_trade_value * regression.beta / (short_price * context.pricing_factor),
                    short_price * context.pricing_factor,
                    Side.SHORT,
                ),
            ]
        else:
            actions = []

        for action in actions:
            context.action_queue.add_action(action)


def main() -> None:
    context = Context()
    topics = context.external_events_topics

    while True:
        logging.debug('main loop')
        if context.action_queue.has_action():
            logging.debug('has action')
            context.action_queue.pop_action()(context)
            continue

        logging.debug('waiting for event'),
        event = context.event_listener.wait()
        logging.debug('received')

        if isinstance(event, ShouldDo):
            event.do(context)
            continue

        if context.state == State.NN and event.topic in (
            topics.LONG_LONG_ORDERBOOK,
            topics.LONG_SHORT_ORDERBOOK,
            topics.SHORT_LONG_ORDERBOOK,
            topics.SHORT_SHORT_ORDERBOOK,
        ):
            CheckResidual()(context)
            continue

        if context.state == State.NN:
            CheckIfOrdersAreOpen()(context)
            continue

        logging.error(
            'Unhandled "(state, event)"  pair: %s %s',
            event,
            context.state,
        )
