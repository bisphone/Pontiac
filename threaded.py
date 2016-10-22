from __future__ import unicode_literals, print_function, division, absolute_import
from pprint import pprint
import threading
import string
import logging
import multiprocessing
from six.moves import queue

import six

import errors
import settings
import taskq
import webservice
import notifier


logger = logging.getLogger(__name__)


class Worker(threading.Thread):
    """ Thread executing tasks from a given tasks queue """
    def __init__(self, tasks, *args, **kwargs):
        daemon = kwargs.pop('daemon', False)
        threading.Thread.__init__(self, *args, **kwargs)
        self.daemon = daemon
        self.tasks = tasks
        self.stop_flag = threading.Event()
        self.start()

    def run(self):
        while not self.stop_flag.is_set():
            try:
                task = self.tasks.get(block=True, timeout=10)
            except queue.Empty:
                pass

            func, args, kwargs = task['func'], task['args'], task['kwargs']
            options = task.get('options', {})
            if 'name' in options:
                self.name = options['name']

            try:
                func(*args, **kwargs)
            except Exception as e:
                # An exception happened in this thread
                logger.exception(e)
            finally:
                # Mark this task as done, whether an exception happened or not
                self.tasks.task_done()
        logger.debug('thread was flagged to stop')


class ThreadPool(object):
    """ Pool of threads consuming tasks from a queue """
    def __init__(self, max_threads):
        self.max_threads = max_threads
        self.tasks = queue.Queue(maxsize=max_threads)
        self.pool = []
        for i in range(min(self.tasks.qsize(), max_threads)):
            worker = Worker(self.tasks, name='worker{}'.format(i+1))
            self.pool.append(worker)

    def add_task(self, func_signature, **options):
        """ Add a task to the queue """
        func, args, kwargs = func_signature['func'], func_signature['args'], func_signature['kwargs']
        # worker threads should be daemonic, so that they exit when the main program exits, and there be no need for joining.
        daemon = options.pop('daemon', True)
        self.tasks.put({'func': func, 'args': args, 'kwargs': kwargs, 'options': options})
        if self.tasks.qsize() > 0 and len(self.pool) < self.max_threads:
            worker = Worker(self.tasks, daemon=daemon, name='worker{}'.format(len(self.pool)+1))
            self.pool.append(worker)

    def map(self, func, args_list):
        """ Add a list of tasks to the queue """
        for args in args_list:
            self.add_task(func, args)

    def stop(self):
        for trd in self.pool:
            trd.stop_flag.set()
            trd.join()

    def wait_completion(self):
        """ Wait for completion of all the tasks in the queue """
        self.tasks.join()


class WebServiceThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        self.qs = kwargs.pop('qs')
        self.daemon = True
        threading.Thread.__init__(self, *args, **kwargs)

    def run(self, *args, **kwargs):
        logger.info('webservice thread started')
        try:
            srv = webservice.Service(qs=self.qs)
            srv.run(*args, **kwargs)
        except errors.PontiacError as e:
            print('Pontiac Error. type: "{}", {}'.format(type(e), e))
        logger.info('webservice thread finished')


def webservice_func(*args, **kwargs):
    logger.info('webservice thread started')
    try:
        srv = webservice.Service(qs=kwargs.pop('qs'))
        srv.run(*args, **kwargs)
    except errors.PontiacError as e:
        print('Pontiac Error. type: "{}", {}'.format(type(e), e))
    logger.info('webservice thread finished')


class NotifierThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        self.queue = kwargs.pop('queue')
        threading.Thread.__init__(self, *args, **kwargs)

    def run(self, *args, **kwargs):
        logger.info('notifier thread started')
        try:
            notifr = notifier.Notifier()
            while True:
                msg = self.queue.get()
                logger.debug('received a new message on notification queue: "{}"'.format(msg))
                try:
                    notifr.notify(msg=msg)
                except errors.DataValidationError as e:
                    print('Data Validation Error: {}'.format(e))
        except errors.PontiacError as e:
            print('Pontiac Error. type: "{}", {}'.format(type(e), e))
        logger.info('notifier thread finished')


def notifier_func(*args, **kwargs):
    logger.info('notifier thread started')
    try:
        notifr = notifier.Notifier()
        while True:
            msg = kwargs['queue'].get()
            logger.debug('received a new message on notification queue: "{}"'.format(msg))
            try:
                notifr.notify(msg=msg)
            except errors.DataValidationError as e:
                print('Data Validation Error: {}'.format(e))
    except errors.PontiacError as e:
        print('Pontiac Error. type: "{}", {}'.format(type(e), e))
    logger.info('notifier thread finished')


def run_multi_thread(args):
    """Run two threads for notification receiver (webservice) and notification processor (notifier)
    """
    logger.info('running in multi-thread mode')
    if args.queuer == 'queue':
        q_class = taskq.MemoryQueue
    elif args.queuer == 'redis':
        q_class = taskq.RedisQueue
    else:
        raise NotImplementedError()

    qs = {
        'notif': q_class(key='notif'),
    }

    pool = ThreadPool(max_threads=sum(settings.THREAD_COUNT.values()))
    logger.info('creating {} webservice threads'.format(settings.THREAD_COUNT['WEBSERVICE']))
    pool.add_task({'func': webservice_func, 'args': (), 'kwargs': {'qs': qs}}, name='webservice', daemon=True)
    logger.info('creating {} notification threads'.format(settings.THREAD_COUNT['NOTIFICATION']))
    for i in range(settings.THREAD_COUNT['NOTIFICATION']):
        pool.add_task({'func': notifier_func, 'args': (), 'kwargs': {'queue': qs['notif']}}, name='notifier{}'.format(i), daemon=True)
    pool.wait_completion()
    pool.stop()
