import dataclasses
import datetime
import enum
import logging
from decimal import Decimal

from frog.analyst import rpc as analyst_rpc
from frog.ordermanager.nobifake import rpc as nobitex_rpc
from frog.ordermanager.types import Fill, OrderId
from frog.square.rpc import RpcClient, RpcError
from frog.tradestore import rpc as tradestore_rpc
from frog.types import Amount, Asset, Pair, Price, Side, Value
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


@dataclasses.dataclass(slots=True)
class Topics:
    long_asset_orderbook: listener.Topic
    short_asset_orderbook: listener.Topic
    account_fill: listener.Topic


class Client(RpcClient):
    analyst = analyst_rpc.Service()
    trade_store = tradestore_rpc.Service()
    nobitex_client = nobitex_rpc.Service()


class CancelOrder(Action):
    def __init__(self, order_id: OrderId) -> None:
        self.order_id = order_id

    def __call__(self, context: 'Context') -> None:
        logging.debug('cancelling order %s', str(self.order_id))
        context.client.nobitex_client.cancel_order(self.order_id)
        context.set_pair_order_to_close(context.order_id_to_order_map[self.order_id].pair)


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
    action_queue: ActionQueue
    client: Client

    # state
    state: State
    order_id_to_order_map: dict[OrderId, Order]
    ####  config

    regression_len: int
    trade_threshold: Decimal
    pricing_factor: Decimal
    wait_period: datetime.timedelta
    long_asset: Asset
    short_asset: Asset
    quote_asset: Asset
    base_trade_value: Value

    @property
    def analyst(self) -> analyst_rpc.Service:
        return self.client.analyst

    @property
    def trade_store(self) -> tradestore_rpc.Service:
        return self.client.trade_store

    @property
    def nobitex_client(self) -> nobitex_rpc.Service:
        return self.client.nobitex_client

    def __init__(
        self,
        regression_len: int,
        trade_threshold: Decimal,
        pricing_factor: Decimal,
        wait_period: datetime.timedelta,
        long_asset: Asset,
        short_asset: Asset,
        quote_asset: Asset,
        base_trade_value: Value,
        client_identity: str,
    ) -> None:
        self.regression_len = regression_len
        self.trade_threshold = trade_threshold
        self.pricing_factor = pricing_factor
        self.wait_period = wait_period
        self.long_asset = long_asset
        self.short_asset = short_asset
        self.quote_asset = quote_asset
        self.base_trade_value = base_trade_value

        self.state = State.NN
        self.action_queue = ActionQueue()
        self.client = Client(client_identity)
        self.order_id_to_order_map = {}
        self.external_events_topics = Topics(
            listener.Topic(f'order_{self.long_pair}'.encode()),
            listener.Topic(f'order_{self.short_pair}'.encode()),
            listener.Topic(f'fill_{client_identity}_'.encode()),
        )
        self.event_listener = listener.Listener(
            [
                self.external_events_topics.long_asset_orderbook,
                self.external_events_topics.short_asset_orderbook,
                self.external_events_topics.account_fill,
            ],
        )
        self.event_listener.initialize()

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

        elif pair == self.short_pair:
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

        elif pair == self.short_pair:
            if self.state == State.NN:
                self.state = State.NY

            elif self.state == State.YN:
                self.state = State.YY

    def run(self):
        while True:
            if self.action_queue.has_action():
                action = self.action_queue.pop_action()
                logging.debug('There is Action: %s', action)
                action(self)
                continue

            event = self.event_listener.wait()

            if event.topic == listener.REMINDER_TOPIC and isinstance(event.data, Action):
                event.data(self)
                continue

            if self.state == State.NN and event.topic in (
                self.external_events_topics.long_asset_orderbook,
                self.external_events_topics.short_asset_orderbook,
            ):
                CheckResidual()(self)
                continue

            if self.state != State.NN and event.topic in (
                self.external_events_topics.long_asset_orderbook,
                self.external_events_topics.short_asset_orderbook,
            ):
                continue

            if self.state != State.NN and event.topic == self.external_events_topics.account_fill:
                UpdateOrderFill(event.data)(self)
                continue

            logging.error(
                'Unhandled "(state, event)"  pair: %s %s',
                event,
                self.state,
            )


class PlaceOrder(Action):
    def __init__(self, pair: Pair, amount: Amount, price: Price, side: Side) -> None:
        self.pair = pair
        self.amount = amount
        self.price = price
        self.side = side
        super().__init__()

    def __call__(self, context: Context) -> None:
        logging.debug('placing order')
        order_id = context.nobitex_client.place_order(
            pair=self.pair,
            side=self.side,
            amount=self.amount,
            price=self.price,
        )
        context.order_id_to_order_map[order_id] = Order(
            amount=self.amount,
            pair=self.pair,
            side=self.side,
            price=self.price,
        )
        context.set_pair_order_to_open(self.pair)
        context.event_listener.add_reminder(context.wait_period, CancelOrder(order_id))
        logging.debug(
            'placed %s order on %s, amount: %s, price: %s.order id: %s.',
            str(self.side),
            str(self.pair.base),
            str(self.amount),
            str(self.price),
            str(order_id),
        )


class CheckResidual(Action):
    def __call__(self, context: Context) -> None:
        logging.debug('checking residual')
        end_time = now().replace(second=0, microsecond=0)
        start_time = end_time - datetime.timedelta(minutes=context.regression_len)

        try:
            long_price = context.trade_store.get(context.long_pair, end_time)
            short_price = context.trade_store.get(context.short_pair, end_time)

        except RpcError:
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
            - regression.beta * (short_price / regression.short_price_normalizer)
        )
        logging.debug('residual is, %s', str(residual))
        logging.debug('regression: %s', str(regression))
        logging.debug('long price: %s, short price: %s', str(long_price), str(short_price))

        if context.trade_threshold >= residual >= -context.trade_threshold:
            return

        should_short_long_asset = context.trade_threshold < residual
        long_pair_side = Side.SHORT if should_short_long_asset else Side.LONG
        short_pair_side = Side.LONG if should_short_long_asset else Side.SHORT
        pf = context.pricing_factor
        long_pair_price = long_price * (pf if should_short_long_asset else 1 / pf)
        short_pair_price = short_price * (1 / pf if should_short_long_asset else pf)
        long_amount = context.base_trade_value / long_pair_price
        assert isinstance(long_amount, Amount)
        short_amount = (context.base_trade_value / short_pair_price) * regression.beta
        assert isinstance(short_amount, Amount)
        context.action_queue.add_action(
            PlaceOrder(
                pair=context.long_pair,
                amount=long_amount,
                price=long_pair_price,
                side=long_pair_side,
            )
        )
        context.action_queue.add_action(
            PlaceOrder(
                pair=context.short_pair,
                amount=short_amount,
                price=short_pair_price,
                side=short_pair_side,
            )
        )


class UpdateOrderFill:
    def __init__(self, fill: Fill) -> None:
        self.fill = fill

    def __call__(self, context: Context) -> None:
        logging.debug('update Order %s fill by %s.', str(self.fill.order_id), str(self.fill.amount))
        order = context.order_id_to_order_map.get(self.fill.order_id)
        if order is None:
            return
        order.filled_amount += self.fill.amount
        if order.filled_amount < order.amount:
            return
        context.order_id_to_order_map.pop(self.fill.order_id)
        context.set_pair_order_to_close(order.pair)
