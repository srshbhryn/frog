import asyncio
import pickle
import dataclasses
from datetime import timedelta
import logging
from queue import Queue
from threading import Thread, Lock
from typing import Any

import zmq
import zmq.asyncio as async_zmq

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
        self.reminder_queue: asyncio.Queue = asyncio.Queue(maxsize=0)
        self.lock = Lock()

    def initialize(self) -> None:
        logging.debug('initializing')
        Thread(
            target=self._background_fun,
            args=(self.event_queue, self.reminder_queue),
            daemon=True,
        ).start()
        logging.debug('initialized')

    def wait(self) -> Event:
        _topic, _data = self.event_queue.get()
        logging.debug('received event %s %s', _topic, _data)
        topic = Topic(_topic)
        if topic == REMINDER_TOPIC:
            data = pickle.loads(_data)
        else:
            data = msgpack.loads(_data)

        return Event(Topic(topic), data)

    def _background_fun(
        self,
        event_queue: Queue,
        reminder_queue: asyncio.Queue,
    ) -> None:
        socket = async_zmq.Context().socket(zmq.SUB)
        socket.connect(self.HIGHWAY_URL)
        for topic in self.topics:
            socket.subscribe(topic)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def get_and_create_tasks() -> None:
            while True:
                logging.debug('waiting for reminder')
                timeout, data = await reminder_queue.get()

                async def _task_fun() -> None:
                    try:
                        await asyncio.sleep(timeout)
                    except asyncio.CancelledError:
                        return

                    event_queue.put([REMINDER_TOPIC, data])

                loop.create_task(_task_fun())

        async def main() -> None:
            while True:
                logging.debug('waiting for external_event')
                event_queue.put(await socket.recv_multipart())

        loop.create_task(get_and_create_tasks())
        loop.run_until_complete(main())

    def add_reminder(self, timeout: timedelta, reminder: Any) -> None:
        self.reminder_queue._put((timeout.total_seconds(), pickle.dumps(reminder)))
