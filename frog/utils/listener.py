import logging
import pickle
import dataclasses
import threading
from datetime import timedelta
from queue import Queue
from threading import Thread
from typing import Any

import zmq

from frog import config
from frog.utils import msgpack


class Topic(bytes):
    pass


@msgpack.dataclass
@dataclasses.dataclass(slots=True)
class Event:
    topic: Topic
    data: Any


REMINDER_TOPIC = Topic(b'REMINDER')


class Reminder(Event):
    def __init__(self, data: Any) -> None:
        super().__init__(REMINDER_TOPIC, data)


class Listener:
    HIGHWAY_URL = f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}'

    def __init__(self, topics: list[Topic]) -> None:
        self.topics = topics
        self.event_queue: Queue = Queue(maxsize=0)

    def initialize(self) -> None:
        Thread(
            target=self._background_fun,
            args=(self.event_queue,),
            daemon=True,
        ).start()

    def wait(self) -> Event:
        logging.debug('waiting for event...')
        _topic, _data = self.event_queue.get()
        logging.debug('received %s', _topic)
        topic = Topic(_topic)
        if topic == REMINDER_TOPIC:
            data = pickle.loads(_data)
        else:
            data = msgpack.loads(_data)

        return Event(Topic(topic), data)

    def _background_fun(
        self,
        event_queue: Queue,
    ) -> None:
        socket = zmq.Context().socket(zmq.SUB)
        for topic in self.topics:
            socket.subscribe(topic)
        socket.connect(self.HIGHWAY_URL)
        while True:
            event_queue.put(socket.recv_multipart())

    def add_reminder(self, timeout: timedelta, reminder: Any) -> None:
        threading.Timer(
            timeout.total_seconds(),
            lambda: self.event_queue.put((REMINDER_TOPIC, pickle.dumps(reminder))),
        ).start()
