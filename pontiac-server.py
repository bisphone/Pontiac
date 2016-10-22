#!/usr/bin/env python

from __future__ import unicode_literals, print_function, division, absolute_import
from pprint import pprint
import sys
import argparse
import logging
import logging.config

import settings
import threaded

try:
    logging.config.dictConfig(settings.LOGGING)
except Exception as e:
    print('Error in logging configuration: {}'.format(e))
    sys.exit(1)

logger = logging.getLogger(__name__)
__version__ = '0.1'


def main():
    parser = argparse.ArgumentParser(prog='pontiac', description='push notification service')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1, help='increase verbosity level')
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__))
    parser.add_argument('--queuer', choices=['queue', 'redis'], default='queue')
    parser.add_argument('--executer', choices=['thread', 'process'], default='thread')

    try:
        args = parser.parse_args()
    except Exception as e:
        parser.error(e)

    logging.raiseExceptions = 1 if settings.DEBUG else 0  # turn on logging errors while debugging

    if args.executer == 'thread':
        threaded.run_multi_thread(args)
    else:
        raise NotImplementedError('currently only threaded task execution is supported')


if __name__ == '__main__':
    main()
