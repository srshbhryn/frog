import pathlib

from frog.config import DATA_DIR


DEFAULT_AUTO_FIELD='django.db.models.AutoField'
INSTALLED_APPS = ("frog.tradestore.db",)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR.joinpath('tradestore.sqlite3'),
    }
}


TIME_ZONE = 'UTC'
USE_TZ = True
