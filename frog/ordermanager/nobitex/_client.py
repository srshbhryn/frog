import enum
import logging
import time
import typing

import requests


RETRY_WAIT_PERIOD = 2
NUMBER_OF_RETRIES = 3


def handle_exception(func):
    def wrapper(*args, **kwargs):
        counter = NUMBER_OF_RETRIES
        while True:
            try:
                return func(*args, **kwargs)
            except requests.RequestException as e:
                if counter == 0:
                    raise
                counter -= 1
                logging.exception('RequestException happened.')
                if e.response is not None:
                    logging.error('response body: "%s."', e.response.text)
                time.sleep(RETRY_WAIT_PERIOD)
    return wrapper


class Client:
    base_url = 'https://api.nobitex.ir'

    class Type(enum.Enum):
        PUBLIC = 0
        PRIVATE = 1

    class Method(enum.Enum):
        GET = 'get'
        POST = 'post'
        DELETE = 'delete'

    class Error(Exception):
        pass

    def __init__(self, token: str, name: str) -> None:
        self.token = token
        self.name = name
        self.initialize()

    def initialize(self) -> None:
        self.sessions: dict[Client.Type, requests.Session] = {
            Client.Type.PUBLIC: requests.Session(),
            Client.Type.PRIVATE: requests.Session(),
        }
        self.sessions[Client.Type.PUBLIC].headers = {
            'content-type': 'application/json',
            'user-agent': f'TraderBot/{self.name}',
        }
        self.sessions[Client.Type.PRIVATE].headers = {
            **self.sessions[Client.Type.PUBLIC].headers,
            'Authorization': f'Token {self.token}',
        }

    @handle_exception
    def request(
        self,
        typ: Type,
        method: Method,
        url: str,
        data: typing.Optional[dict] = None,
    ) -> dict:
        response = self.sessions[typ].request(
            method=method.value,
            url=self.base_url + url,
            json=data,
        )
        response.raise_for_status()
        response_data = response.json()
        if not response_data['status'] == 'ok':
            raise Client.Error(response_data)
        return response_data
