import dataclasses
import datetime
import enum
import logging
import time
from decimal import Decimal

from frog.analyst import rpc as analyst_rpc
from frog.ordermanager.nobitex import rpc as nobitex_rpc
from frog.ordermanager.types import Fill, OrderId
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
    YN = (AssetState.OPEN_ORDER, AssetState.NO_ORDER)
    NY = (AssetState.NO_ORDER, AssetState.OPEN_ORDER)
    YY = (AssetState.OPEN_ORDER, AssetState.OPEN_ORDER)


class Action:
    def __call__(self, _: 'Context') -> None:
        raise NotImplementedError


class ChangeState(Action):
    def __init__(self, state: State) -> None:
        self._state = state

    def __call__(self, context: 'Context') -> None:
        context.state = self._state


@dataclasses.dataclass(slots=True)
class Topics:
    long_asset_orderbook: listener.Topic
    short_asset_orderbook: listener.Topic
    long_asset_fill: listener.Topic
    short_asset_fill: listener.Topic


class Client(RpcClient):
    analyst = analyst_rpc.Service()
    trade_store = tradestore_rpc.Service()
    nobitex_client = nobitex_rpc.Service()


class CancelOrder(Action):
    def __init__(self, order: 'Order') -> None:
        self.order = order

    def __call__(self, context: 'Context') -> None:
        raise NotImplementedError


@dataclasses.dataclass(slots=True)
class Order:
    pair: Pair
    side: Side
    amount: Amount
    price: Price
    filled_amount: Amount = Amount('0')


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

    external_events_topics: Topics

    # helpers
    event_listener: listener.Listener
    action_queue: ActionQueue = ActionQueue()
    client: Client = Client()

    # state
    state: State = State.NN
    order_id_to_order_map: dict[OrderId, Order] = {}
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
        self.external_events_topics = Topics(
            listener.Topic(f'order_{self.long_pair}'.encode()),
            listener.Topic(f'order_{self.short_pair}'.encode()),
            listener.Topic(f'fill_{self.long_pair}'.encode()),
            listener.Topic(f'fill_{self.short_pair}'.encode()),
        )
        self.event_listener = listener.Listener(
            [
                self.external_events_topics.long_asset_orderbook,
                self.external_events_topics.short_asset_orderbook,
                self.external_events_topics.long_asset_fill,
                self.external_events_topics.short_asset_fill,
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
            if self.state == State.YN:
                self.state = State.NN

            elif self.state == State.YY:
                self.state = State.NY

        elif pair == self.long_pair:
            if self.state == State.NY:
                self.state = State.NN

            elif self.state == State.YY:
                self.state = State.YN

    def set_pair_order_to_open(self, pair: Pair) -> None:
        if pair == self.long_pair:
            if self.state == State.NN:
                self.state = State.YN

            elif self.state == State.NY:
                self.state = State.YY

        elif pair == self.long_pair:
            if self.state == State.NN:
                self.state = State.NY

            elif self.state == State.YN:
                self.state = State.YY

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
            )
        )
        context.order_id_to_order_map[order_id] = Order(
            amount=self.amount,
            pair=self.pair,
            side=self.side,
            price=self.price,
        )
        context.event_listener.add_reminder(context.wait_period, CancelOrder(order_id))


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

        regression = context.analyst.get_regression(context.long_pair, context.short_pair, start_time, end_time)

        residual = (
            long_price / regression.long_price_normalizer
            - regression.alpha
            - regression.beta * short_price / regression.short_price_normalizer
        )
        if 1 + context.trade_threshold >= residual >= 1 - context.trade_threshold:
            return

        should_short_long_asset = 1 + context.trade_threshold < residual
        long_pair_side = Side.SHORT if should_short_long_asset else Side.LONG
        short_pair_side = Side.LONG if should_short_long_asset else Side.SHORT

        pf = context.pricing_factor
        long_pair_price = long_price * (pf if should_short_long_asset else 1 / pf)
        short_pair_price = short_price * (1 / pf if should_short_long_asset else pf)

        context.action_queue.add_action(
            PlaceOrder(
                context.long_pair,
                context.base_trade_value / long_pair_price,
                long_pair_price,
                long_pair_side,
            )
        )

        context.action_queue.add_action(
            PlaceOrder(
                context.short_pair,
                regression.beta * context.base_trade_value / short_pair_price,
                short_pair_price,
                short_pair_price,
            )
        )


class UpdateOrderFill:
    def __init__(self, fill: Fill) -> None:
        self.fill = fill

    def __call__(self, context: Context) -> None:
        order = context.order_id_to_order_map.get(self.fill.order_id)
        if order is None:
            return
        order.filled_amount += self.fill.amount
        if order.filled_amount < order.amount:
            return
        context.order_id_to_order_map.pop(self.fill.order_id)
        context.set_pair_order_to_close(order.pair)


def main() -> None:
    context = Context()
    topics = context.external_events_topics

    while True:
        logging.debug('main loop')
        if context.action_queue.has_action():
            logging.debug('has action')
            context.action_queue.pop_action()(context)
            continue

        logging.debug('waiting for event')
        event = context.event_listener.wait()
        logging.debug('received')

        if event.topic == listener.REMINDER_TOPIC and isinstance(event.data, Action):
            event.data(context)
            continue

        if context.state == State.NN and event.topic in (
            topics.long_asset_orderbook,
            topics.short_asset_orderbook,
        ):
            CheckResidual()(context)
            continue

        if context.state != State.NN and event.topic in (
            topics.long_asset_orderbook,
            topics.short_asset_orderbook,
        ):
            continue

        if context.state != State.NN and event.topic in (
            topics.long_asset_fill,
            topics.short_asset_fill,
        ):
            UpdateOrderFill(event.data)(context)
            continue

        logging.error(
            'Unhandled "(state, event)"  pair: %s %s',
            event,
            context.state,
        )
