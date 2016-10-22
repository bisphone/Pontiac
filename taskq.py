from __future__ import unicode_literals, print_function, division, absolute_import
from pprint import pprint
import logging
import time
from six.moves import queue

import simplejson as json
import redis

import settings
import errors


logger = logging.getLogger(__name__)


class TaskQueue(object):
    """Basic interface to be implemented by a keyed task queuer class.
    Given a particular key at construction time, this class should point the put
    or get requests to the queue for that particular key. This is basically a
    key-value store in which values are individual queues.
    task objects should be a python dict holding primitive values which can be
    easily serialized to json or other formats.
    If a task queue is full, put requests should be dropped silently.
    If a task queue is empty, get requests should block.
    """
    def __init__(self, *args, **kwargs):
        self.key = kwargs.pop('key')

    def put(self, task):
        raise NotImplementedError()

    def get(self):
        raise NotImplementedError()

    def size(self):
        raise NotImplementedError()

    def close(self):
        """Close or delete this particular queue"""
        raise NotImplementedError()


class MemoryQueue(TaskQueue):
    """TaskQueue implementation using python builtin Queue module"""
    queues = {}

    def __init__(self, *args, **kwargs):
        TaskQueue.__init__(self, *args, **kwargs)
        if self.key not in MemoryQueue.queues:
            MemoryQueue.queues[self.key] = queue.Queue(maxsize=settings.QUEUE_MAX_SIZE)

    def put(self, task):
        q = MemoryQueue.queues[self.key]
        try:
            q.put(task, False)
        except (queue.Empty, queue.Full) as e:
            logger.warning('Queue operation failed: {}'.format(e))

    def get(self):
        q = MemoryQueue.queues[self.key]
        try:
            item = q.get(True)
            q.task_done()
            return item
        except (queue.Empty, queue.Full) as e:
            logger.warning('Queue operation failed: {}'.format(e))

    def size(self):
        q = MemoryQueue.queues[self.key]
        return q.qsize()

    def close(self):
        del MemoryQueue.queues[self.key]


class RedisQueue(TaskQueue):
    conn = None

    def __init__(self, *args, **kwargs):
        TaskQueue.__init__(self, *args, **kwargs)
        params = {
            'host': settings.REDIS['host'],
            'port': settings.REDIS.get('port', 6379),
            'db': settings.REDIS.get('db', 0),
        }
        if settings.REDIS.get('password'):
            params.update({'password': settings.REDIS['password']})

        if RedisQueue.conn is None:
            try:
                RedisQueue.conn = redis.Redis(**params)  # redis.StrictRedis(**params)
            except redis.RedisError as e:
                raise errors.DependencyError('failed to connect to redis server: {}'.format(e))

        self.max_size = int(settings.REDIS.get('max_size', 0))
        # TODO: implement redis pipeline interface to increase performance

    def serialize(self, task):
        """Serialize the task object to a string to be able to put it in redis"""
        return json.dumps(task)

    def deserialize(self, task):
        return json.loads(task)

    def put(self, task):
        try:
            RedisQueue.conn.lpush(self.key, self.serialize(task))
            if self.max_size:
                RedisQueue.conn.ltrim(self.key, 0, self.max_size - 1)
        except redis.RedisError as e:
            raise errors.DependencyError('failed to push to redis server: {}'.format(e))

    def get(self):
        try:
            item = RedisQueue.conn.brpop(self.key)[1]
        except redis.RedisError as e:
            raise errors.DependencyError('failed to pop from redis server: {}'.format(e))
        return self.deserialize(item)

    def size(self):
        try:
            sz = int(RedisQueue.conn.llen(self.key))
        except redis.RedisError as e:
            raise errors.DependencyError('failed to get length from redis server: {}'.format(e))
        return sz

    def close(self):
        try:
            RedisQueue.conn.ltrim(self.key, 0, 0)
        except redis.RedisError as e:
            raise errors.DependencyError('failed to delete list from redis server: {}'.format(e))
