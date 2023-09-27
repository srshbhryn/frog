import enum
import logging
import typing
import threading
from queue import Queue

import msgpack
import zmq

from .conf import BACKEND_PORT, FRONTEND_PORT, NO_SUCH_SERVICE, REGISTER


class RpcError(Exception):
    class Code(enum.Enum):
        OK = b'0'
        BAD_REQUEST = b'1'
        UNEXPECTED_ERROR = b'-1'
        NOT_AVAILABLE = b'4'
        INVALID_METHOD = b'5'
        NO_SERVICE = b'8'

    def __init__(
        self,
        code: typing.Optional[Code] = None,
        msg: typing.Optional[str] = None,
    ) -> None:
        self.code = code or self.Code.BAD_REQUEST
        self.msg = msg or self.__class__.__name__


class RpcService:
    topic: bytes
    square_host: str
    rpc_methods: typing.ClassVar[dict[str, typing.Callable]] = {}

    Err = RpcError

    @classmethod
    def register(cls, method: callable) -> None:
        cls.rpc_methods[method.__name__] = method
        return method

    def __init__(self) -> None:
        pass

    def run_server(self) -> None:
        socket = zmq.Context().socket(zmq.REQ)
        socket.connect(f'tcp://{self.square_host}:{BACKEND_PORT}')
        socket.send_multipart((REGISTER, self.topic))

        while True:
            try:
                (
                    client_identity,
                    method_name_b,
                    args_kwargs_b,
                ) = socket.recv_multipart()
                method_name = method_name_b.decode()
                args_kwargs = msgpack.loads(args_kwargs_b)
                args = args_kwargs['args']
                kwargs = args_kwargs['kwargs']

                if method_name not in self.__class__.rpc_methods:
                    error_msg = f'No Such Method named as {method_name}'
                    f', client: {client_identity}'
                    logging.error(error_msg)
                    return_value = error_msg.encode()
                    code = RpcError.Code.INVALID_METHOD
                else:
                    return_value = msgpack.dumps(
                        self.__class__.rpc_methods[method_name](*args, **kwargs),
                    )
                    code = RpcError.Code.OK

            except RpcError as e:
                logging.warning('Handled rpc Error', exc_info=True)
                code = e.code
                return_value = e.msg.encode()
            except Exception as e:
                logging.exception('Unhandled rpc Error')
                code = RpcError.Code.UNEXPECTED_ERROR
                return_value = f'{e}'.encode()
            socket.send_multipart((client_identity, code, return_value))

    def init_client(self, socket: zmq.Socket) -> None:
        self.response_queue = Queue(maxsize=128)
        self.socket = socket
        for name in self.__class__.rpc_methods:
            self.__class__.rpc_methods[name] = self._request(name)

    def _request(self, name: str) -> callable:
        def wrapped(*args, **kwargs) -> callable:
            args_kwargs_b = msgpack.dumps({'args': args, 'kwargs': kwargs})
            self.socket.send_multipart((self.topic, name.encode(), args_kwargs_b))
            code, return_value = self.response_queue.get()
            if code == NO_SUCH_SERVICE:
                raise RpcError(RpcError.Code.NO_SERVICE)
            if not code == RpcError.Code.OK:
                raise RpcError(code, return_value.decode())
            return msgpack.loads(return_value)

        return wrapped


class RpcClient:
    square_host: str

    def __init__(self) -> None:
        self.socket = zmq.Context().socket(zmq.PAIR)
        self.socket.connect(f'tcp://{self.square_host}:{FRONTEND_PORT}')
        self.topic_to_services_map: dict[bytes, RpcService] = {}
        for service in (
            attr
            for attr in self.__dict__
            if isinstance(
                attr,
                RpcService,
            )
        ):
            service.init_client(self.socket)
            self.topic_to_services_map[service.topic] = service

        threading.Thread(target=self.run_client, args=(), daemon=True).start()

    def run_client(self) -> None:
        while True:
            try:
                (topic, code, return_value) = self.socket.recv_multipart()
                self.topic_to_services_map[topic].response_queue.put_nowait((code, return_value))
            except Exception:
                logging.exception('error in rpc client')
