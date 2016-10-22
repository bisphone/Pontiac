from __future__ import unicode_literals, print_function, division, absolute_import
from pprint import pprint
import logging
import copy

import pyfcm


logger = logging.getLogger(__name__)


class FCMError(Exception):
    """Base class for FCM exceptions"""
    pass


class NotConnectedError(FCMError):
    """Exception to be raised when connection to notification service has been severed"""
    pass


class ProxyError(FCMError):
    """Error in proxy configuration"""
    pass


class ResultError(FCMError):
    """Error in result object returned from FCM"""
    pass


class FCM(object):
    """Encapsulation of FCM calls

    With FCM, you can send two types of messages to clients:
    1. Notification messages, sometimes thought of as "display messages."
    2. Data messages, which are handled by the client app.
    Client app is responsible for processing data messages. Data messages have only custom key-value pairs. (Python dict)
    Data messages let developers send up to 4KB of custom key-value pairs.
    Use notification messages when you want FCM to handle displaying a notification on your app's behalf.
    Use data messages when you just want to process the messages only in your app.
    PyFCM can send a message including both notification and data payloads.
    In such cases, FCM handles displaying the notification payload, and the client app handles the data payload.
    """
    MAX_PAYLOAD_SIZE = 4 * 1024

    def __init__(self, **kwargs):
        params = {'api_key': kwargs['api_key']}
        if 'proxy' in kwargs and kwargs['proxy']:
            proxies = kwargs['proxy'] if isinstance(kwargs['proxy'], list) else [kwargs['proxy']]
            proxy_dict = {}
            for proxy in proxies:
                if proxy.startswith('http://'):
                    proxy_dict.update({'http': proxy})
                elif proxy.startswith('https://'):
                    proxy_dict.update({'https': proxy})
                else:
                    raise ProxyError('proxy type not supported')
            if bool(proxy_dict):
                params.update({'proxy_dict': proxy_dict})
        self.service = pyfcm.FCMNotification(**params)

    def notify_single(self, **kwargs):
        registration_ids = kwargs['registration_id']
        payload = copy.deepcopy(kwargs['payload'])
        message_title = payload.pop('message_title', None)
        message_body = payload.pop('message_body', None)

        params = {
            'registration_id': kwargs['registration_id'],
            'message_title': message_title,
            'message_body': message_body,
            'data_message': payload,
            'low_priority': False,
            'delay_while_idle': False,
            'time_to_live': None,
            'dry_run': False
        }
        # TODO: ensure that payload size is not larger than max FCM notification payload size

        try:
            result = self.service.notify_single_device(**params)
        except pyfcm.errors.FCMError as e:
            raise FCMError(e)

        if result['success'] != 1:
            raise ResultError('Message failed to be processed by FCM. {} expected, {} failed'.format(
                int(result['success']) + int(result['failure']), int(result['failure'])))
        return result['results']

    def notify_multiple(self, **kwargs):
        # Send to multiple devices by passing a list of ids.
        assert isinstance(kwargs['registration_ids'], list)
        registration_ids = kwargs['registration_ids']
        payload = copy.deepcopy(kwargs['payload'])
        message_title = payload.pop('message_title', None)
        message_body = payload.pop('message_body', None)

        params = {
            'registration_ids': kwargs['registration_ids'],
            'message_title': message_title,
            'message_body': message_body,
            'data_message': payload,
            'low_priority': False,
            'delay_while_idle': False,
            'time_to_live': None,
            'sound': None,
            'dry_run': False
        }

        try:
            result = self.service.notify_multiple_devices(**params)
        except pyfcm.errors.FCMError as e:
            raise FCMError(e)

        if int(result['success']) + int(result['failure']) != len(registration_ids):
            raise FCMError('This should not happen')

        if result['success'] != len(registration_ids):
            raise ResultError('Some messages failed to be processed by FCM. {} expected, {} failed'.format(
                int(result['success']) + int(result['failure']), int(result['failure'])))
        return result['results']

    @staticmethod
    def result_str(results):
        result_strs = []
        for num, result in enumerate(results):
            result_strs.append('Result #{} msg id {}, reg id {}, error {}'.format(num + 1, result.get('message_id'),
                result.get('registration_id'), result.get('error')))
        return '\n'.join(result_strs)
