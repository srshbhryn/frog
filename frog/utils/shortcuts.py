import datetime

import pytz


def now() -> datetime.datetime:
    datetime.datetime.now(tz=pytz.UTC)
