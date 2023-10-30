import asyncio
import dataclasses
from datetime import timedelta
import logging
from queue import Queue
from threading import Thread

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
    data: bytes


REMINDER_TOPIC = Topic(b'REMINDER')


class Reminder(Event):
    topic = REMINDER_TOPIC


class Listener:

    def __init__(self, topics: list[Topic]) -> None:
        self.topics = topics
        self.queue: Queue = Queue()
        self.reminders: list[asyncio.Task[None]] = []
        self.socket = async_zmq.Context().socket(zmq.SUB)
        self.socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')
        self._subscribe()
        logging.debug('connected')

        Thread(target=self._background_fun, args=(), daemon=True).start()

    def wait(self) -> Event:
        topic, data = self.queue.get()
        logging.debug('received event %s %s', topic, data)
        return Event(Topic(topic), msgpack.loads(data))

    def _background_fun(self) -> None:
        async def main() -> None:
            while True:
                logging.debug('waiting for external_event')
                self.queue.put(await self.socket.recv_multipart())

        asyncio.run(main())

    def add_reminder(self, timeout: timedelta, reminder: Reminder) -> asyncio.Task[None]:
        async def _task_fun() -> None:
            try:
                await asyncio.sleep(timeout.total_seconds())
            except asyncio.CancelledError:
                return
            else:
                self.queue.put([REMINDER_TOPIC, msgpack.dumps(reminder)])

        task = asyncio.create_task(_task_fun())
        self.reminders.append(task)
        return task

    def cancel_all_reminders(self) -> None:
        for task in self.reminders:
            task.cancel()
        self.reminders = []

    def _subscribe(self) -> None:
        for topic in self.topics:
            self.socket.subscribe(topic)
        logging.debug('subscribed')

    def __del__(self) -> None:
        self.socket.close()
