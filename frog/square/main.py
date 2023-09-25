import logging
import threading

import zmq

from .conf import BACKEND_PORT, FRONTEND_PORT, NO_SUCH_SERVICE, REGISTER


class Square:
    topic_to_identity_map: dict[bytes, bytes]

    def get_topic_from_identity(self, identity: bytes) -> bytes | None:
        for topic, _identity in self.topic_to_identity_map.items():
            if _identity == identity:
                return topic
        return None

    def __init__(self) -> None:
        self.topic_to_identity_map = {}
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
                    client_identity,
                    *data,
                ) = self.backend_socket.recv_multipart()
                if client_identity == REGISTER:
                    topic = data[0]
                    self.topic_to_identity_map[topic] = server_identity
                    continue
                self.frontend_socket.send_multipart((client_identity, topic, *data))
            except:
                logging.exception()
                self.frontend_socket.poll

    def frontend(self) -> None:
        while True:
            try:
                (
                    client_identity,
                    topic,
                    *data,
                ) = self.frontend_socket.recv_multipart()

                server_identity = self.topic_to_identity_map.get(topic)
                if server_identity is None:
                    self.frontend_socket.send_multipart(
                        (client_identity, NO_SUCH_SERVICE),
                    )
                self.backend_socket.send_multipart(
                    (server_identity, client_identity, *data),
                )
            except:
                logging.exception()
