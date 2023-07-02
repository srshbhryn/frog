from typing import Dict

import requests
import logging

import requests


logger = logging.getLogger()


class NobitexClientError(Exception):
    pass


def handle_exception(func):
    def wrapper(*args, **kwargs):
        self: Nobitex = args[0]
        while True:
            try:
                response = func(*args, **kwargs)
            except requests.RequestException as e:
                logger.error(e)
                if e.response is not None:
                    logger.error(e.response.text)
            return response
    return wrapper


class Nobitex:
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
            Nobitex.TYPE.public: requests.Session(),
            Nobitex.TYPE.private: requests.Session(),
        }
        self.sessions[Nobitex.TYPE.public].headers = {
            'content-type': 'application/json',
            'user-agent': f'TraderBot/{self.name}'
        }
        self.sessions[Nobitex.TYPE.private].headers = {
            **self.sessions[Nobitex.TYPE.public].headers,
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
