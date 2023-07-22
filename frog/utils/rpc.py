import pickle
import logging

import zmq


class RpcError(Exception):
    def __init__(self, code, msg) -> None:
        self.code = code
        self.msg = msg


class ZmqRpc:
    is_client = False
    uri = None
    bind_uri = None
    rpc_methods = {}

    @classmethod
    def register(cls, method):
        cls.rpc_methods[method.__name__] = method
        return method

    def __init__(self) -> None:
        self.rpc_methods = {}
        if self.is_client:
            self._init_client()
        else:
            self._run_server()

    def _init_client(self):
        self.socket = zmq.Context().socket(zmq.REP)
        self.socket.connect(self.uri)
        for name, method in self.rpc_methods.items():
            self.rpc_methods[name] = self._request(name, method)


    def _request(self, name: str, method):
        def wrapped(*args):
            self.socket.send_multipart([name.encode(), pickle.dumps(args)])
            response = self.socket.recv_multipart()
            if not response[0] == b'0':
                raise RpcError(int(response[0].decode()), f'{response[1:]}')
            return pickle.loads(response[1])

        return wrapped

    def _run_server(self):
        socket = zmq.Context().socket(zmq.REP)
        socket.bind(self.bind_uri)
        while True:
            try:
                request = socket.recv_multipart()
                method_name = request[0].decode()
                if not method_name in self.rpc_methods:
                    raise RpcError(4, f'bad request {request}')
                socket.send_multipart([b'0'] + [pickle.dumps(self.rpc_methods[method_name](
                    *(pickle.loads(request[1]))
                ))])
            except RpcError as e:
                logging.warning(f'bad request {request}', exc_info=True)
                socket.send_multipart([str(e.code).encode(), e.msg.encode()])
            except Exception as e:
                logging.error(f'bad request {request}', exc_info=True)
                socket.send_multipart([b'-1', f'{e}'.encode()])
