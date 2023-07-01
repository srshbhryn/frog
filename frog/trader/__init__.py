
from .client import Nobitex


class Trader:
    def __init__(self, token) -> None:
        self.token = token
        self.client = Nobitex(token, 'frog0.1')

    def open_long(self, symbol, amount, price) -> None:
        base, quote = symbol.split('-')
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/market/orders/add',
            data={
                'type': 'buy',
                'srcCurrency': base,
                'dstCurrency': quote,
                'amount': amount,
                'price': price,
            },
        )
        assert response['status'] == 'ok'

    def _get_spot_balance(self, asset):
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/users/wallets/balance',
            data={'currency': asset},
        )
        assert response['status'] == 'ok'
        return response['balance']

    def close_all_long(self, symbol,  price) -> None:
        base, quote = symbol.split('-')
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/market/orders/add',
            data={
                'type': 'buy',
                'srcCurrency': base,
                'dstCurrency': quote,
                'amount': self._get_spot_balance(base),
                'price': price,
            },
        )
        assert response['status'] == 'ok'

    def open_short(self, symbol, amount, price) -> None:
        base, quote = symbol.split('-')
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/margin/orders/add',
            data={
                'srcCurrency': base,
                'dstCurrency': quote,
                'amount': amount,
                'price': price,
            },
        )
        assert response['status'] == 'ok'
        self.symbol_to_short_amount[symbol] = response['order']['amount']

    def _get_position_id_and_liability(self, symbol):
        base, quote = symbol.split('-')
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.get,
            url=f'/positions/list?srcCurrency={base}&dstCurrency={quote}&status=active',
        )
        print(response)
        assert response['status'] == 'ok'
        return response['positions'][0]['id'], response['positions'][0]['liability']

    def close_all_short(self, symbol, price) -> None:
        position_id, liability = self._get_position_id_and_liability(symbol)
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url=f'/positions/{position_id}/close',
            data={
                'amount': liability,
                'price': price,
            },
        )
        assert response['status'] == 'ok'

    def available_quote(self) -> float:
        return 20_000_000
