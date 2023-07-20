import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRET_KEY = "6few3nci_q_o@l1dlbk81%wcxe!*6r29yu629&d97!hiqat9fa"

DEFAULT_AUTO_FIELD='django.db.models.AutoField'
INSTALLED_APPS = ("frog.tradestore.db",)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

TIME_ZONE = 'UTC'
USE_TZ = True
