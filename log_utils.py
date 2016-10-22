from __future__ import unicode_literals, print_function, division, absolute_import
from pprint import pprint
import logging
import threading
from six.moves import queue

import redis

import settings


class RequireDebugFalse(logging.Filter):
    def filter(self, record):
        return not settings.DEBUG


class RequireDebugTrue(logging.Filter):
    def filter(self, record):
        return settings.DEBUG


class AsyncHandler(threading.Thread):
    """A log handler class, which takes another handler instance as parameter,
    puts all logging records in a queue, and read from the queue in a separate thread
    and call actual handler to process the record.
    """

    def __init__(self, handler):
        self._handler = handler
        self._queue = queue.Queue()
        self.daemon = True
        self.start()

    def run(self):
        while True:
            record = self._queue.get(True)
            self._handler.emit(record)

    def emit(self, record):
        self._queue.put(record)


class RedisLogHandler:
    """Log handler which puts log entries in a redis list
    """

    def __init__(self, host=None, port=None, db=0, log_key='log_key'):
        self._formatter = logging.Formatter()
        self._redis = redis.Redis(host=host or 'localhost', port=port or 6379, db=db)
        self._redis_list_key = log_key
        self._level = logging.DEBUG

    def handle(self, record):
        try:
            self._redis.lpush(self._redis_list_key, self._formatter.format(record))
        except:
            # can't do much here--probably redis have stopped responding...
            # TODO: what do other handlers do when errors occur?
            pass

    def setFormatter(self, formatter):
        self._formatter = formatter

    @property
    def level(self):
        return self._level

    def setLevel(self, val):
        self._level = val
