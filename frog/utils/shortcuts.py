import datetime

import pytz


def now() -> datetime.datetime:
    return datetime.datetime.now(tz=pytz.UTC)
