#!/usr/bin/env python

from __future__ import unicode_literals, print_function, division, absolute_import
from pprint import pprint
import argparse
import string
import logging

import six
import simplejson as json
import pem
import fcm_service
import apns_service


logger = logging.getLogger(__name__)
__version__ = '0.1'


class JsonAction(argparse.Action):
    """An argparse action which validates input value as a JSON string
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(JsonAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            j = json.loads(values)
            val = json.dumps(j, ensure_ascii=True, indent=4, separators=(',', ': '), sort_keys=True)
            setattr(namespace, self.dest, val)
        except Exception as e:
            parser.error(e)


class PemAction(argparse.Action):
    """An argparse action which validates input value as a PEM file
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(PemAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            pem_parsed = pem.parse_file(values)
            if not isinstance(pem_parsed, list) or len(pem_parsed) != 1:
                raise TypeError('PEM file is not valid')
            setattr(namespace, self.dest, values)
        except Exception as e:
            parser.error(e)


class ProxyAction(argparse.Action):
    """An argparse action which validates input value as a valid proxy address
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(ProxyAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            if values:
                proto, rest = values.split('://', 2)
                proto = proto.lower()
                if proto not in ['socks', 'socks5', 'http', 'https']:
                    raise TypeError('Proxy is not valid')
                addr, port = rest.split(':', 2)
                port = int(port)
                setattr(namespace, self.dest, '{}://{}:{}'.format(proto, addr, port))
        except Exception as e:
            parser.error('Proxy address is not valid: {}'.format(e))


def apns_token(token_str):
    """Validate an APNS token"""
    token_str = token_str.strip()
    if not isinstance(token_str, six.string_types) or len(token_str) != 64 or not all(c in string.hexdigits for c in token_str):
        raise argparse.ArgumentTypeError('APNS token is not valid')
    return token_str


def main():
    parser = argparse.ArgumentParser(prog='pushak', description='push notification services wrapper')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1, help='increase verbosity level')
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__))

    subparsers = parser.add_subparsers(dest='subparser_name', help='sub-command help')
    parser_fcm = subparsers.add_parser('fcm', help='fcm help')
    parser_apns = subparsers.add_parser('apns', help='apns help')

    parser_fcm.add_argument('--api-key', '-k', required=True, help='API key')
    parser_fcm.add_argument('--reg-id', '-i', nargs='+', help='registration ids')
    parser_fcm.add_argument('--proto', choices=['http', 'xmpp'], default='xmpp', help='transfer protocol')
    parser_fcm.add_argument('--proxy', action='append', help='http or https proxy server for connecting to firebase')
    # low_priority
    # delay_while_idle
    # time_to_live
    # restricted_package_name
    # dry_run
    parser_fcm.add_argument('payload', action=JsonAction, help='data payload')
    parser_fcm.set_defaults(func=handle_fcm)

    parser_apns.add_argument('--cert', action=PemAction, required=True, help='certificate file')
    parser_apns.add_argument('--key', action=PemAction, required=True, help='private key file')
    parser_apns.add_argument('--proxy', action=ProxyAction, help='http, https or socks proxy server for connecting to APNS server')
    parser_apns.add_argument('--release', action='store_true', default=False, help='whether release certs been used instead of development')
    parser_apns.add_argument('--token', '-t', type=apns_token, nargs='+', help='client token as hex string')
    parser_apns.add_argument('payload', action=JsonAction, help='data payload')
    parser_apns.set_defaults(func=handle_apns)

    try:
        args = parser.parse_args()
    except Exception as e:
        parser.error(e)

    args.func(args)


def handle_fcm(args):
    if args.verbosity > 1:
        print('FCM push notification service')
        print('data payload:\n{}'.format(args.payload))

    fcm_obj = fcm_service.FCM(api_key=args.api_key, proxy=args.proxy)
    try:
        if len(args.reg_id) > 1:
            results = fcm_obj.notify_multiple(registration_ids=args.reg_id, payload=json.loads(args.payload))
        else:
            results = fcm_obj.notify_single(registration_id=args.reg_id[0], payload=json.loads(args.payload))

        if args.verbosity > 1:
            print(fcm_service.FCM.result_str(results))
    except fcm_service.FCMError as e:
        print('Caught FCM error: {}'.format(e))


def handle_apns(args):
    if args.verbosity > 1:
        print('APNS push notification service')
        print('data payload:\n{}'.format(args.payload))

    try:
        apns_obj = apns_service.APNS(cert=args.cert, key=args.key, proxy=args.proxy, release=args.release)
        if len(args.token) > 1:
            apns_obj.notify_multiple(token=args.token, payload=json.loads(args.payload))
        else:
            apns_obj.notify_single(token=args.token[0], payload=json.loads(args.payload))
    except apns_service.APNSError as e:
        print('Caught APNS error: {}'.format(e))

    if args.verbosity > 1:
        print(apns_service.APNS.feedback_messages_str(apns_obj.feedback_messages()))


if __name__ == '__main__':
    main()
