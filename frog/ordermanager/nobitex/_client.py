from typing import Dict
import time
import requests
import logging

import requests


logger = logging.getLogger()


class NobitexClientError(Exception):
    pass


def handle_exception(func):
    def wrapper(*args, **kwargs):
        counter = 3
        while counter:
            try:
                return func(*args, **kwargs)
            except requests.RequestException as e:
                logger.error(e)
                if e.response is not None:
                    logger.error(e.response.text)
                time.sleep(2)
                cnt -= 1
        raise e
    return wrapper


class NobitexIntegration:
    base_url = 'https://api.nobitex.ir'

    class TYPE:
        public = 0
        private = 1

    class METHOD:
        get = 'get'
        post = 'post'
        delete = 'delete'

    def __init__(self, token: str, name: str) -> None:
        self.token = token
        self.name = name
        self.initialize()

    def initialize(self) -> None:
        self.sessions: Dict[int,requests.Session] = {
            NobitexIntegration.TYPE.public: requests.Session(),
            NobitexIntegration.TYPE.private: requests.Session(),
        }
        self.sessions[NobitexIntegration.TYPE.public].headers = {
            'content-type': 'application/json',
            'user-agent': f'TraderBot/{self.name}'
        }
        self.sessions[NobitexIntegration.TYPE.private].headers = {
            **self.sessions[NobitexIntegration.TYPE.public].headers,
            'Authorization': f'Token {self.token}'
        }

    @handle_exception
    def _request(self, type, method, url, data=None):
        response = self.sessions[type].request(
            method=method,
            url=self.base_url + url,
            json=data,
        )
        response.raise_for_status()
        response = response.json()
        if not response['status'] == 'ok':
            raise NobitexClientError(response)
        return response




class Trader:
    def __init__(self, token) -> None:
        self.token = token
        self.client = NobitexIntegration(token, 'frog0.2')

    def _get_open_long_data(self, symbol, amount, price):
        base, quote = symbol.split('-')
        return {
            'type': 'buy',
            'srcCurrency': base,
            'dstCurrency': quote,
            'amount': amount,
            'price': price,
        }

    def open_long(self, symbol, amount, price) -> None:
        self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/market/orders/add',
            data=self._get_open_long_data(symbol, amount, price)
        )

    def _get_spot_balance(self, asset) -> str:
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/users/wallets/balance',
            data={'currency': asset},
        )
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
        self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/market/orders/add',
            data=self._get_close_all_long_data(symbol, price),
        )

    def _get_open_short_data(self, symbol, amount, price):
        base, quote = symbol.split('-')
        return {
            'srcCurrency': base,
            'dstCurrency': quote,
            'amount': amount,
            'price': price,
        }

    def open_short(self, symbol, amount, price) -> None:
        self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url='/margin/orders/add',
            data=self._get_open_short_data(symbol, amount, price),
        )

    def _get_position_id_and_liability(self, symbol):
        base, quote = symbol.split('-')
        response = self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.get,
            url=f'/positions/list?srcCurrency={base}&dstCurrency={quote}&status=active',
        )
        return response['positions'][0]['id'], response['positions'][0]['liability']

    def _get_close_all_short_data(self, amount, price):
        return {
            'amount': amount,
            'price': price,
        }

    def close_all_short(self, symbol, price) -> None:
        position_id, liability = self._get_position_id_and_liability(symbol)
        self.client._request(
            type=self.client.TYPE.private,
            method=self.client.METHOD.post,
            url=f'/positions/{position_id}/close',
            data=self._get_close_all_short_data(liability, price),
        )

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
