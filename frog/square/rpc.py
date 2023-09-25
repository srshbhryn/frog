import enum
import logging
import pickle
import typing

import zmq

from .conf import BACKEND_PORT, FRONTEND_PORT, REGISTER


class RpcError(Exception):
    class Code(enum.Enum):
        OK = b'0'
        BAD_REQUEST = b'1'
        UNEXPECTED_ERROR = b'-1'
        NOT_AVAILABLE = b'4'
        INVALID_METHOD = b'5'

    def __init__(
        self,
        code: typing.Optional[Code] = None,
        msg: typing.Optional[str] = None,
    ) -> None:
        self.code = code or self.Code.BAD_REQUEST
        self.msg = msg or self.__class__.__name__


def register(cls, method):
    cls.rpc_methods[method.__name__] = method
    return method


class ZmqRpc:
    is_client = False
    topic: bytes
    square_host: str
    rpc_methods: typing.ClassVar[dict[str, typing.Callable]] = {}

    Err = RpcError

    def __init__(self) -> None:
        if self.is_client:
            self._init_client()
        else:
            self._run_server()

    def _init_client(self):
        self.socket = zmq.Context().socket(zmq.REQ)
        self.socket.connect(f'tcp://{self.square_host}:{FRONTEND_PORT}')
        for name in self.__class__.rpc_methods:
            self.__class__.rpc_methods[name] = self._request(name)

    def _request(self, name: str):
        def wrapped(*args):
            self.socket.send_multipart([name.encode(), pickle.dumps(args)])
            response = self.socket.recv_multipart()
            if not response[0] == RpcError.Code.OK:
                raise RpcError(response[0], response[0].decode())
            return pickle.loads(response[1])

        return wrapped

    def _run_server(self):
        socket = zmq.Context().socket(zmq.REQ)
        socket.connect(f'tcp://{self.square_host}:{BACKEND_PORT}')
        socket.send_multipart((REGISTER, self.topic))

        while True:
            try:
                request = socket.recv_multipart()
                method_name = request[0].decode()
                if method_name not in self.__class__.rpc_methods:
                    error_msg = f'No Such Method named as {method_name}'
                    logging.error(error_msg)
                    socket.send_multipart(
                        [RpcError.Code.INVALID_METHOD, error_msg.encode()],
                    )
                socket.send_multipart(
                    [
                        RpcError.Code.OK,
                        pickle.dumps(
                            self.__class__.rpc_methods[method_name](*pickle.loads(request[1])),
                        ),
                    ],
                )
            except RpcError as e:
                logging.warning('Handled rpc Error', exc_info=True)
                socket.send_multipart([e.code, e.msg.encode()])
            except Exception as e:
                logging.exception('Unhandled rpc Error')
                socket.send_multipart([RpcError.Code.UNEXPECTED_ERROR, f'{e}'.encode()])
