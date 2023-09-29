import logging
import threading

import zmq

from .conf import BACKEND_PORT, FRONTEND_PORT, NO_SUCH_SERVICE, REGISTER


class Square:
    def get_topic_from_identity(self, identity: bytes) -> bytes | None:
        for topic, _identity in self.topic_to_identity_map.items():
            if _identity == identity:
                return topic
        return None

    def __init__(self) -> None:
        self.topic_to_identity_map: dict[bytes, bytes] = {}
        context = zmq.Context()

        self.frontend_socket = context.socket(zmq.ROUTER)
        self.frontend_socket.bind(f'tcp://*:{FRONTEND_PORT}')

        self.backend_socket = context.socket(zmq.ROUTER)
        self.backend_socket.bind(f'tcp://*:{BACKEND_PORT}')

    def run(self) -> None:
        threading.Thread(target=self.backend, args=(), daemon=True).start()
        self.frontend()

    def backend(self) -> None:
        while True:
            try:
                (
                    server_identity,
                    _,
                    client_identity,
                    *data,
                ) = self.backend_socket.recv_multipart()

                if client_identity == REGISTER:
                    topic = data[0]
                    self.topic_to_identity_map[topic] = server_identity
                    logging.info('registered service: %s: %s', topic, server_identity)
                    continue
                topic = self.get_topic_from_identity(server_identity)
                logging.debug(
                    'backend msg \ts: %s\tc: %s ',
                    server_identity,
                    client_identity,
                )
                self.frontend_socket.send_multipart(
                    (client_identity, topic, *data),
                )
            except:
                logging.exception('Failed backend read.')

    def frontend(self) -> None:
        while True:
            try:
                (
                    client_identity,
                    _,
                    topic,
                    *data,
                ) = self.frontend_socket.recv_multipart()
                logging.debug(
                    'frontend msg\tt: %s\tc: %s ',
                    topic,
                    client_identity,
                )

                server_identity = self.topic_to_identity_map.get(topic)
                if server_identity is None:
                    self.frontend_socket.send_multipart(
                        (client_identity, topic, NO_SUCH_SERVICE, b'n'),
                    )
                self.backend_socket.send_multipart(
                    (server_identity, b'', client_identity, *data),
                )
            except:
                logging.exception('Failed frontend read')
