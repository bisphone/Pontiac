import multiprocessing
from six.moves import queue

DEBUG = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'standard': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            # 'datefmt': '%Y-%m-%d %H:%M:%S.%f %z'
        },
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s(%(name)s:%(lineno)s) P %(process)d (%(processName)s) T %(thread)d (%(threadName)s) %(message)s'
        },
        'email': {
            'format': 'Timestamp: %(asctime)s\nModule: %(module)s\nLine: %(lineno)d\nMessage: %(message)s',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'log_utils.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'log_utils.RequireDebugFalse'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'stderr': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            # 'filters': ['require_debug_true'],
        },
        'file_watched': {
            'level': 'DEBUG',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': './logs/pontiac.log',
            'formatter': 'verbose',
        },
        'file_rotating': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': './logs/pontiac.log',
            'maxBytes': 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'socket_tcp': {
            'level': 'DEBUG',
            'class': 'logging.handlers.SocketHandler',
            'host': 'localhost',
            'port': '12345',
            'formatter': 'standard',
            'filters': ['require_debug_false'],
        },
        'syslog': {
            'level': 'DEBUG',
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
            'facility': 'LOG_USER',
            'formatter': 'standard',
            'filters': ['require_debug_false'],
        },
        'smtp': {
            'level': 'DEBUG',
            'class': 'logging.handlers.SMTPHandler',
            'mailhost': '(localhost, 25)',
            'fromaddr': 'pontiac@domain.tld',
            'toaddrs': ['support@domain.tld'],
            'subject': 'Pontiac Message',
            'credentials': '(username, password)',
            'formatter': 'email',
            'filters': ['require_debug_false'],
        },
        'http': {
            'level': 'DEBUG',
            'class': 'logging.handlers.HTTPHandler',
            'host': 'localhost',
            'url': '/log',
            'method': 'GET',
            'filters': ['require_debug_false'],
        },
        # 'queue': {  # only available on python 3.2+
        #     'level': 'DEBUG',
        #     'class': 'logging.handlers.QueueHandler',
        #     'filters': ['require_debug_false'],
        # },
        'logutils_queue': {
            'level': 'DEBUG',
            'class': 'logutils.queue.QueueHandler',
            'queue': queue.Queue()
        },
        # 'logutils_redis': {
        #     'level': 'DEBUG',
        #     'class': 'logutils.redis.RedisQueueHandler',
        #     'key': 'pontiac.logging',
        # },
        'redis': {
            'level': 'DEBUG',
            'class': 'log_utils.RedisLogHandler',
            'host': 'localhost',
            'port': 6379,
            'log_key': 'pontiac.logging',
        },
        'rlog_redis': {
            'level': 'DEBUG',
            'class': 'rlog.RedisHandler',
            'host': 'localhost',
            'password': 'password',
            'port': 6379,
            'channel': 'pontiac_logs'
        },
        'logstash': {
            'level': 'DEBUG',
            'class': 'logstash.LogstashHandler',
            'host': 'localhost',
            'port': 5959,
            'version': 1,
            'message_type': 'logstash',
            'fqdn': False,
            'tags': None,
        },
    },
    'loggers': {
        '': {
            'handlers': ['stderr'],
            'level': 'DEBUG',
            'propagate': True
        },
        'webservice': {
            'handlers': ['stderr', 'file_watched'],
            'level': 'DEBUG',
            'propagate': False
        },
        'notifier': {
            'handlers': ['stderr', 'file_watched'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['stderr', 'file_watched'],
        'level': 'NOTSET',
    }
}

HTTP_SOCKET = {
    'host': '0.0.0.0',
    'port': 1234
}

SCHEMA = {
    'NOTIFICATION': 'schemas/notification.schema.json',
}

QUEUE_MAX_SIZE = 1000000

REDIS = {
    'host': 'localhost',
    'port': 6379,
    'password': '',  # empty string or None disables
    'db': 0,
    'max_size': 0,  # 0 disables
    'expires': 300  # in seconds
}

try:
    CPU_COUNT = multiprocessing.cpu_count()
except NotImplementedError:
    CPU_COUNT = 1

THREAD_COUNT = {
    'WEBSERVICE': 1,
    'NOTIFICATION': CPU_COUNT * 2,
}

FCM = {
    #'proxy': 'http://localhost:8000',
    'api_key': '-api-key-',
    'proto': 'xmpp',
    # low_priority
    # delay_while_idle
    # time_to_live
    # restricted_package_name
    # dry_run
}

APNS = {
    #'proxy': 'http://localhost:8000',
    'cert': 'path/to/cert.pem',
    'key': 'path/to/key.pem',
    'dist': False,
}
