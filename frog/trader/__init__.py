
from .client import Nobitex


class Trader:
    def __init__(self, token) -> None:
        self.token = token
        self.symbol_to_long_amount = {}
        self.symbol_to_short_amount = {}
        self.symbol_to_short_id = {}
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
        self.symbol_to_long_amount[symbol] = response['order']['amount']

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
                'amount': self.symbol_to_long_amount[symbol],
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
        self.symbol_to_short_id[symbol] = response['order']['id']

    def close_all_short(self, symbol, price) -> None:
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url=f'/positions/{self.symbol_to_short_id[symbol]}/close',
            data={
                'amount': self.symbol_to_short_amount[symbol],
                'price': price,
            },
        )
        assert response['status'] == 'ok'

    def available_quote(self) -> float:
        return 20_000_000
