import datetime
import functools

import pytz
import zmq


def now() -> datetime.datetime:
    return datetime.datetime.now(tz=pytz.UTC)


_zmq_context = zmq.Context()


def get_zmq_context() -> zmq.Context:
    return _zmq_context
