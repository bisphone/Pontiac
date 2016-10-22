from __future__ import unicode_literals, print_function, division, absolute_import
from pprint import pprint
import string
import logging
import datetime

import six
import simplejson as json
import jsonschema
import pem

import settings
import errors
import fcm_service
import apns_service


logger = logging.getLogger(__name__)


def validate_pem_file(pem_file, header=None):
    """Validate a PEM encoded certificate or key
    Optionally check if it contains a particular header line.
    """
    pem_parsed = pem.parse_file(pem_file)
    if not isinstance(pem_parsed, list) or len(pem_parsed) != 1:
        return False
    if header:
        first_line = open(pem_file).readline()
        if header not in first_line:
            return False
    return True


def validate_json(json_str, schema=None):
    """Validate a json string
    Optionally check against given json schema.
    """
    try:
        json_obj = json.loads(json_str)
        json_str = json.dumps(json_obj, ensure_ascii=True, indent=4, separators=(',', ': '), sort_keys=True)
    except Exception as e:
        return False
    if schema:
        try:
            jsonschema.validate(json_str, schema)
        except jsonschema.ValidationError:
            return False
    return True


def validate_apns_token(token_str):
    """Validate an APNS token
    These are 32 byte identifiers encoded as a hex string.
    """
    if not isinstance(token_str, six.string_types):
        return False
    token_str_stripped = token_str.strip()
    if len(token_str_stripped) != 64 or not all(c in string.hexdigits for c in token_str_stripped):
        return False
    token_str = token_str_stripped
    return True


class Notifier(object):
    """Abstraction for various types of notification service
    """

    def __init__(self):
        self.connect_fcm()
        self.connect_apns()

    def connect_fcm(self):
        params = {
            'api_key': settings.FCM['api_key'],
        }
        if 'proxy' in settings.FCM and settings.FCM['proxy']:
            params.update({'proxy': settings.FCM['proxy']})
        logger.debug('connecting to fcm service')
        self.fcm_obj = fcm_service.FCM(**params)

    def connect_apns(self):
        for pem_file in [settings.APNS['cert'], settings.APNS['key']]:
            if not validate_pem_file(pem_file):
                raise errors.ConfigurationError('APNS PEM file is not valid: {}'.format(pem_file))

        params = {
            'cert': settings.APNS['cert'],
            'key': settings.APNS['key'],
            'release': settings.APNS['dist'],
        }
        if 'proxy' in settings.APNS and settings.APNS['proxy']:
            params.update({'proxy': settings.APNS['proxy']})
        logger.debug('connecting to apns service')
        self.apns_obj = apns_service.APNS(**params)

    def notify(self, *args, **kwargs):
        msg = kwargs.pop('msg')
        expiry_time = msg.pop('expiry_time', None)
        if expiry_time:
            try:
                expiry = datetime.datetime.strptime(expiry_time, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise errors.DataValidationError('expiry time is not in a valid format')
            if expiry < datetime.datetime.now():
                logger.info('notification message is expired. dropped.')
                return

        srv_type = msg.pop('type', '')
        if srv_type.lower() == 'fcm':
            self.handle_fcm(*args, **msg)
        elif srv_type.lower() == 'apns':
            self.handle_apns(*args, **msg)
        else:
            raise errors.ConfigurationError('invalid notification service type: {}'.format(srv_type))

    def handle_fcm(self, *args, **kwargs):
        try:
            tokens = kwargs['tokens']
            payload = {
                'message_body': kwargs['body'],
            }
            if 'title' in kwargs:
                payload.update({'message_title': kwargs['title']})
            if 'custom_data' in kwargs:
                payload.update({'payload': kwargs['custom_data']})

            if len(tokens) > 1:
                results = self.fcm_obj.notify_multiple(registration_ids=tokens, payload=payload)
            else:
                results = self.fcm_obj.notify_single(registration_id=tokens[0], payload=payload)

            # if args.verbosity > 1:
            #     print(fcm_service.FCM.result_str(results))
        except fcm_service.NotConnectedError as e:
            self.connect_fcm()
        except fcm_service.FCMError as e:
            logger.error('Caught FCM error: {}'.format(e))

    def handle_apns(self, *args, **kwargs):
        try:
            tokens = kwargs['tokens']
            payload = {
                'alert': kwargs['body'],
            }
            if 'badge' in kwargs:
                payload.update({'badge': kwargs['badge']})
            if 'sound' in kwargs:
                payload.update({'sound': kwargs['sound']})
            if 'category' in kwargs:
                payload.update({'category': kwargs['category']})
            if 'silent' in kwargs:
                payload.update({'content_available': kwargs['silent']})

            if len(tokens) > 1:
                self.apns_obj.notify_multiple(token=tokens, payload=payload)
            else:
                self.apns_obj.notify_single(token=tokens[0], payload=payload)
        except apns_service.NotConnectedError as e:
            self.connect_apns()
        except apns_service.APNSError as e:
            logger.error('Caught APNS error: {}'.format(e))

        # if args.verbosity > 1:
        #     print(apns_service.APNS.feedback_messages_str(self.apns_obj.feedback_messages()))
