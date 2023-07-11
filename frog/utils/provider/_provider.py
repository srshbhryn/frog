import logging
import time
import enum


class Provider:
    class Topics(enum.Enum):
        pass

    def __init__(self) -> None:
        pass

    def get(self, topic: Topics, *args):
        pass

    def provide(self):
        pass

    def run(self, sleep_time):
        pass
