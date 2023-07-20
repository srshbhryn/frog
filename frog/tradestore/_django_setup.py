#!/usr/bin/env python
import os
import sys


def setup():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "frog.tradestore._django_settings")
    import django
    django.setup()
    from django.core.management import execute_from_command_line
    execute_from_command_line(['frog/tradestore/_django_setup.py', 'migrate'])


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "frog.tradestore._django_settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
