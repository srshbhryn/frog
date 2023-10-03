import enum
import logging
import threading
import time
import typing
import uuid
from queue import Queue

import zmq

from frog import config
from frog.utils import msgpack
from frog.utils.shortcuts import get_zmq_context


class RpcCode(enum.Enum):
    OK = b'0'
    BAD_REQUEST = b'1'
    UNEXPECTED_ERROR = b'-1'
    NOT_AVAILABLE = b'4'
    INVALID_METHOD = b'5'
    NO_SERVICE = b'8'

    @classmethod
    def get_from_value(cls, value: bytes) -> 'RpcCode':
        for c in cls:
            if c.value == value:
                return c
        return None


class RpcError(Exception):
    def __init__(
        self,
        code: typing.Optional[RpcCode] = None,
        msg: typing.Optional[str] = None,
    ) -> None:
        self.code = code or RpcCode.BAD_REQUEST
        self.msg = msg or self.__class__.__name__


class RpcService:
    topic: bytes
    rpc_methods: typing.ClassVar[dict[str, typing.Callable]] = {}
    Err = RpcError

    @classmethod
    def register(cls, method: callable) -> None:
        cls.rpc_methods[method.__name__] = method
        return method

    def __init__(self) -> None:
        self.topic = b'service_' + self.topic

    def run_server(self) -> None:
        requests_socket: zmq.Socket = get_zmq_context().socket(zmq.SUB)
        requests_socket.subscribe(self.topic)
        requests_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')

        responses_socket: zmq.Socket = get_zmq_context().socket(zmq.PUB)
        responses_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XSUB_PORT}')

        while True:
            try:
                (
                    topic,
                    client_identity,
                    method_name_b,
                    args_kwargs_b,
                ) = requests_socket.recv_multipart()

                method_name = method_name_b.decode()
                args_kwargs = msgpack.loads(args_kwargs_b)
                args = args_kwargs['args']
                kwargs = args_kwargs['kwargs']

                if method_name not in self.__class__.rpc_methods:
                    error_msg = f'No Such Method named as {method_name}'
                    logging.error(error_msg)
                    return_value = error_msg.encode()
                    code = RpcCode.INVALID_METHOD
                else:
                    return_value = msgpack.dumps(
                        self.__class__.rpc_methods[method_name](self, *args, **kwargs),
                    )
                    code = RpcCode.OK

            except RpcError as e:
                logging.warning('Handled rpc Error', exc_info=True)
                code = e.code
                return_value = e.msg.encode()
            except Exception as e:
                logging.exception('Unhandled rpc Error')
                code = RpcCode.UNEXPECTED_ERROR
                return_value = f'{e}'.encode()
            responses_socket.send_multipart(
                (
                    client_identity,
                    topic,
                    code.value,
                    return_value,
                ),
            )

    def init_client(self, requests_queue: Queue) -> None:
        self.response_queue = Queue(maxsize=128)
        self.request_queue = requests_queue
        for name in self.__class__.rpc_methods:
            setattr(self, name, self._request(name))

    def _request(self, name: str) -> callable:
        def wrapped(*args, **kwargs) -> callable:
            args_kwargs_b = msgpack.dumps({'args': args, 'kwargs': kwargs})
            self.request_queue.put((self.topic, name.encode(), args_kwargs_b))
            code, return_value = self.response_queue.get()
            if not code == RpcCode.OK:
                raise RpcError(code, return_value.decode())
            return msgpack.loads(return_value)

        return wrapped


class RpcClient:
    def __init__(self) -> None:
        self.key = uuid.uuid4().hex[:16].encode()  # Client identity

        topic_to_response_queues_map: dict[bytes, Queue] = {}
        requests_queue = Queue(maxsize=128)

        for service in (
            attr
            for attr in self.__class__.__dict__.values()
            if isinstance(
                attr,
                RpcService,
            )
        ):
            service.init_client(requests_queue)
            topic_to_response_queues_map[service.topic] = service.response_queue

        threading.Thread(
            target=self.run_client_responses_loop,
            args=(topic_to_response_queues_map,),
            daemon=True,
        ).start()
        threading.Thread(
            target=self.run_client_requests_loop,
            args=(requests_queue,),
            daemon=True,
        ).start()
        time.sleep(1)

    def run_client_responses_loop(self, topic_to_response_queues_map) -> None:
        responses_socket: zmq.Socket = get_zmq_context().socket(zmq.SUB)
        responses_socket.subscribe(self.key)
        responses_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')

        while True:
            try:
                (_, topic, code, return_value) = responses_socket.recv_multipart()
                topic_to_response_queues_map[topic].put_nowait(
                    (RpcCode.get_from_value(code), return_value),
                )
            except Exception:
                logging.exception('error in rpc client response')

    def run_client_requests_loop(self, requests_queue) -> None:
        requests_socket: zmq.Socket = get_zmq_context().socket(zmq.PUB)
        requests_socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XSUB_PORT}')

        while True:
            try:
                topic, *data = requests_queue.get()
                requests_socket.send_multipart((topic, self.key, *data))
            except Exception:
                logging.exception('error in rpc client request')
