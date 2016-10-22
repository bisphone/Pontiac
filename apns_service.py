from __future__ import unicode_literals, print_function, division, absolute_import
from pprint import pprint
import logging
import copy
import time

import apns
import socks


logger = logging.getLogger(__name__)


class APNSError(Exception):
    """Base class for APNS exceptions"""
    pass


class NotConnectedError(APNSError):
    """Exception to be raised when connection to notification service has been severed"""
    pass


class APNS(object):
    """Encapsulation of FCM calls
    """
    MAX_PAYLOAD_SIZE = 2 * 1024

    def __init__(self, **kwargs):
        self.cert = kwargs['cert']
        self.key = kwargs['key']
        self.release = kwargs.get('release', False)
        params = {
            'use_sandbox': not self.release,
            'cert_file': self.cert,
            'key_file': self.key,
        }

        if 'proxy' in kwargs and kwargs['proxy']:
            proxy_type, proxy_addr = kwargs['proxy'].split('://', 1)
            proxy_types = {
                'http': socks.HTTP,
                'socks4': socks.SOCKS4,
                'socks5': socks.SOCKS5
            }
            addr, port = proxy_addr.split(':', 2)
            socks.set_default_proxy(proxy_types[proxy_type], addr, int(port))
            apns.socket = socks.socksocket  # apns lib dos not support proxies. have to monkeypatch.

        try:
            self.service = apns.APNs(**params)
        except Exception as e:
            raise APNSError(e)

    def notify_single(self, **kwargs):
        token = kwargs['token']
        payload_dict = copy.deepcopy(kwargs['payload'])

        params = {
            'alert': payload_dict.pop('alert', None),
            'badge': payload_dict.pop('badge', None),
            'sound': payload_dict.pop('sound', None),
            'category': payload_dict.pop('category', None),
            'content_available': payload_dict.pop('content-available', False),
        }
        params['custom'] = payload_dict
        payload = apns.Payload(**params)
        # TODO: ensure that payload size is not larger than max APNS notification payload size

        try:
            ret = self.service.gateway_server.send_notification(token, payload)
            return ret
        except Exception as e:
            raise APNSError(e)

    def notify_multiple(self, **kwargs):
        payload_dict = copy.deepcopy(kwargs['payload'])

        params = {
            'alert': payload_dict.pop('alert', None),
            'badge': payload_dict.pop('badge', None),
            'sound': payload_dict.pop('sound', None),
            'category': payload_dict.pop('category', None),
            'content_available': payload_dict.pop('content-available', False),
        }
        params['custom'] = payload_dict
        payload = apns.Payload(**params)

        frame = apns.Frame()
        identifier = 1
        expiry = time.time() + 3600
        priority = 10

        try:
            for token in kwargs['token']:
                frame.add_item(token, payload, identifier, expiry, priority)
            ret = self.service.gateway_server.send_notification_multiple(frame)
            return ret
        except Exception as e:
            raise APNSError(e)

    def feedback_messages(self):
        # feedback messages need a separate connection
        params = {
            'use_sandbox': not self.release,
            'cert_file': self.cert,
            'key_file': self.key,
        }

        try:
            service = apns.APNs(**params)
            res = []
            for (token_hex, fail_time) in service.feedback_server.items():
                res.append((token_hex, fail_time))
            return res
        except Exception as e:
            raise APNSError(e)

    @staticmethod
    def feedback_messages_str(msgs):
        result_strs = []
        for num, msg in enumerate(msgs):
            result_strs.append('Msg #{}: {}'.format(num, msg))
        return '\n'.join(result_strs)
