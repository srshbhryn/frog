import asyncio
import pickle
from dataclasses import dataclass
from datetime import timedelta
from threading import Thread

import zmq
import zmq.asyncio as async_zmq

from frog import config


class Topic(bytes):
    pass


@dataclass(slots=True)
class Event:
    topic: Topic
    data: bytes


reminder_topic = Topic(b'REMINDER')


class Reminder(Event):
    topic = reminder_topic


class Listener:
    _reminder_topic = Topic(b'REMINDER')

    def __init__(self, topics: list[Topic]) -> None:
        self.topics = topics
        self.inter_process_uri = 'inproc://inter_process_uri'
        self.client_socket = zmq.Context().socket(zmq.SUB)
        self.client_socket.connect(self.inter_process_uri)
        self.server_socket = async_zmq.Context().socket(zmq.PUB)
        self.reminders: list[asyncio.Task[None]] = []
        Thread(target=self._background_fun, args=(), daemon=True).start()

    def wait(self) -> Event:
        topic, data = self.client_socket.recv_multipart()
        return Event(Topic(topic), data)

    def _background_fun(self) -> None:
        async def main() -> None:
            self.server_socket.connect(self.inter_process_uri)
            self._subscribe()
            while True:
                await self.server_socket.send_multipart(
                    await self.socket.recv_multipart(),
                )

        asyncio.run(main())

    def add_reminder(self, timeout: timedelta, reminder: Reminder) -> None:
        async def task() -> None:
            try:
                await asyncio.sleep(timeout.total_seconds())
            except asyncio.CancelledError:
                return
            else:
                self.server_socket.send_multipart(
                    [self._reminder_topic, pickle.dumps(reminder)],
                )

        self.reminders.append(asyncio.create_task(task()))

    def cancel_all_reminders(self) -> None:
        for task in self.reminders:
            task.cancel()
        self.reminders = []

    def _subscribe(self) -> None:
        self.socket = async_zmq.Context().socket(zmq.SUB)
        self.socket.connect(f'tcp://{config.HIGHWAY_HOST}:{config.HIGHWAY_XPUB_PORT}')

        for topic in self.topics:
            if topic == self._reminder_topic:
                continue
            self.socket.subscribe(topic)

    def __del__(self) -> None:
        self.socket.close()
