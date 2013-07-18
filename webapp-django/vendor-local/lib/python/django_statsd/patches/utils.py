from django_statsd.clients import statsd
from functools import partial


def wrapped(method, key, *args, **kw):
    with statsd.timer(key):
        return method(*args, **kw)


def wrap(method, key, *args, **kw):
    return partial(wrapped, method, key, *args, **kw)
