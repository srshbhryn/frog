import dataclasses
from decimal import Decimal
import typing


from frog.types import Asset, Pair, Amount, Side
from frog.ordermanager.types import Fill

from ._client import Client


PositionId = typing.NewType('PositionId', int)


@dataclasses.dataclass
class Position:
    position_id: PositionId
    pair: Pair
    side: Side
    liability: Amount
    leverage: Decimal


class PositionManger:
    def __init__(self, client: Client) -> None:
        self._position_id_to_position_map: dict[PositionId, Position] = {}
        self._pair_side_to_position_id_map: dict[tuple[Pair, Side], PositionId] = {}
        self._client = client
        self._load_positions()

    def _load_positions(self) -> None:
        has_next = True
        page = 1
        while has_next:
            response = self._client.request(
                Client.Type.PRIVATE,
                Client.Method.GET,
                f'/positions/list?status=active&page={page}',
            )
            page += 1
            has_next = response['has_next']
            for position_data in response['positions']:
                position_id = PositionId(position_data['id'])
                is_short = position_data['side'] == 'sell'
                pair = Pair(
                    Asset(position_data['srcCurrency']),
                    Asset(position_data['dstCurrency']),
                )
                side = Side.SHORT if is_short else Side.LONG
                liability = Amount(position_data['liability'])
                leverage = Decimal(position_data['leverage'])
                position = Position(
                    position_id=position_id,
                    pair=pair,
                    side=side,
                    liability=liability,
                    leverage=leverage,
                )
                self._position_id_to_position_map[position_id] = position
                self._pair_side_to_position_id_map[(pair, side)] = position_id

    def get_position_by_pair_side(self, pair: Pair, side: Side) -> typing.Optional[Position]:
        position_id = self._pair_side_to_position_id_map.get((pair, side))
        if position_id is None:
            return None
        return self._position_id_to_position_map[position_id]

    def get_position_by_id(self, position_id: PositionId) -> Position:
        return self._position_id_to_position_map[position_id]

    def apply_close_order_fill_to_position(
        self,
        pair: Pair,
        side: Side,
        fill: Fill,
    ) -> None:
        position = self.get_position_by_pair_side(pair, -side)
        if position is None:
            return
        reduced_liability = (
            fill.amount
            if position == Side.SHORT
            else Amount(
                (fill.amount * fill.price).as_decimal(),
            )
        )
        position.liability -= reduced_liability
