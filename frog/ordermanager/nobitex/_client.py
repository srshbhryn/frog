import enum
import logging
import threading
import time
import typing

import requests
import zmq

from frog import config

logger = logging.getLogger()


def handle_exception(func):
    def wrapper(*args, **kwargs):
        counter = 3
        while True:
            try:
                return func(*args, **kwargs)
            except requests.RequestException as e:
                if counter == 0:
                    raise
                counter -= 1
                logger.exception('RequestException happened.')
                if e.response is not None:
                    logger.error('response body: "%s."', e.response.text)
                time.sleep(2)
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
        threading.Thread(target=self.fill_collector, args=(), daemon=True).start()

    def fill_collector(self) -> None:
        socket = zmq.Context().socket(zmq.PUB)
        socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XSUB_PORT}')

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
