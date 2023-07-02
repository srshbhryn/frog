import logging

from .client import Nobitex


class Trader:
    def __init__(self, token) -> None:
        self.token = token
        self.client = Nobitex(token, 'frog0.1')

    def _get_open_long_data(symbol, amount, price):
        base, quote = symbol.split('-')
        return {
                'type': 'buy',
                'srcCurrency': base,
                'dstCurrency': quote,
                'amount': amount,
                'price': price,
            }

    def open_long(self, symbol, amount, price) -> None:
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/market/orders/add',
            data=self._get_open_long_data(symbol, amount, price)
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

    def _get_close_all_long_data(self, symbol, price):
        base, quote = symbol.split('-')
        return {
                'type': 'sell',
                'srcCurrency': base,
                'dstCurrency': quote,
                'amount': self._get_spot_balance(base),
                'price': price,
            }

    def close_all_long(self, symbol, price) -> None:
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/market/orders/add',
            data=self._get_close_all_long_data(),
        )
        assert response['status'] == 'ok'

    def _get_open_short_data(self, symbol, amount, price):
        base, quote = symbol.split('-')
        return{
            'srcCurrency': base,
            'dstCurrency': quote,
            'amount': amount,
            'price': price,
        }

    def open_short(self, symbol, amount, price) -> None:
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/margin/orders/add',
            data=self._get_open_short_data(symbol, amount, price),
        )
        assert response['status'] == 'ok'

    def _get_position_id_and_liability(self, symbol):
        base, quote = symbol.split('-')
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.get,
            url=f'/positions/list?srcCurrency={base}&dstCurrency={quote}&status=active',
        )
        assert response['status'] == 'ok'
        return response['positions'][0]['id'], response['positions'][0]['liability']

    def _get_close_all_short_data(self, amount, price):
        return {
            'amount': amount,
            'price': price,
        }

    def close_all_short(self, symbol, price) -> None:
        position_id, liability = self._get_position_id_and_liability(symbol)
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url=f'/positions/{position_id}/close',
            data=self._get_close_all_short_data(liability, price),
        )
        assert response['status'] == 'ok'

    def available_quote(self) -> float:
        return 20_000_000


class MarketTrader(Trader):

    def make_market_order(self, data: dict) -> dict:
        data.pop('price', None)
        data['execution'] = 'market'
        return data

    def _get_open_long_data(self, symbol, amount, price):
        data = super()._get_open_long_data(symbol, amount, price)
        return self.make_market_order(data)

    def _get_close_all_long_data(self, symbol, price):
        data = super()._get_close_all_long_data(symbol, price)
        return self.make_market_order(data)

    def _get_open_short_data(self, symbol, amount, price):
        data = super()._get_open_short_data(symbol, amount, price)
        return self.make_market_order(data)

    def _get_close_all_short_data(self, amount, price):
        data = super()._get_close_all_short_data(amount, price)
        return self.make_market_order(data)
