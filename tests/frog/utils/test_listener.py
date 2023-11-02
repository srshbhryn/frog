from datetime import timedelta

from frog.utils.listener import Listener, REMINDER_TOPIC


def fun(x):
    return x + 12


def test_reminder():
    listener = Listener([])
    listener.HIGHWAY_URL = 'inproc://test'
    listener.initialize()

    listener.add_reminder(timedelta(), fun)
    event = listener.wait()
    assert event.topic == REMINDER_TOPIC
    assert event.data(22) == 34
