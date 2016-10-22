#!/usr/bin/env python
from __future__ import unicode_literals, print_function, division, absolute_import
from pprint import pprint
import logging
import sys
import cgi

import simplejson as json
import jsonschema

from twisted.web import server, resource
from twisted.internet import reactor, endpoints

import settings
import errors
import taskq


logger = logging.getLogger(__name__)


class GetStat(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        try:
            request.setResponseCode(200)
            request.setHeader(b'content-type', b'text/plain')
            content = 'I am stat\n'
            return content.encode('ascii')
        except Exception as e:
            return resource.ErrorPage(500, 'Error', 'Message: {}'.format(e)).render(request)


class AddNotif(resource.Resource):
    isLeaf = True

    def __init__(self, *args, **kwargs):
        self.queue = kwargs.pop('queue')
        self.number_requests = 0
        try:
            self.schema = json.loads(open(settings.SCHEMA['NOTIFICATION']).read())
        except (KeyError, IOError, ValueError):
            raise errors.ConfigurationError('invalid json schema document')
        resource.Resource.__init__(self, *args, **kwargs)

    def render_GET(self, request):
        content = '<html><body><p>Please send POST request</p></body></html>'
        return content.encode('ascii')

    def render_POST(self, request):
        self.number_requests += 1
        try:
            data_str = cgi.escape(request.content.read())
            logger.debug('post request data string: "{}"'.format(data_str))
            data_dict = json.loads(data_str)
        except ValueError as e:
            return resource.ErrorPage(400, 'BAD_REQUEST', 'Message: invalid json document').render(request)

        try:
            jsonschema.validate(data_dict, self.schema)
        except jsonschema.ValidationError as e:
            return resource.ErrorPage(400, 'BAD_REQUEST', 'Message: invalid json document').render(request)

        try:
            num_notif = 0
            for notif in data_dict:
                self.queue.put(notif)
                num_notif += 1
            request.setResponseCode(202)
            request.setHeader(b'content-type', b'application/json')
            result = {
                'msg_accepted': num_notif,
                'queue_pending': self.queue.size(),
                'total_requests': self.number_requests
            }
            content = json.dumps(result, ensure_ascii=True, indent=4, separators=(',', ': '), sort_keys=True)
            logger.debug('response string: "{}"'.format(content))
            return content.encode('ascii')
        except Exception as e:
            return resource.ErrorPage(500, 'Error', 'Message: {}'.format(e)).render(request)

    def _responseFailed(self, err, call):
        """To cancel deferred calls on this request"""
        call.cancel()
        logger.warning('async response interrupted: "{}"'.format(err))

    def _delayedRender(self, request):
        request.write("<html><body>Sorry to keep you waiting.</body></html>")
        request.finish()

    def render_PST(self, request):
        # TODO: for pushing asynchronously to redis (or other task queue)
        call = reactor.callLater(5, self._delayedRender, request)
        request.notifyFinish().addErrback(self._responseFailed, call)
        return server.NOT_DONE_YET


def get_root_resource(*args, **kwargs):
    root = resource.Resource()
    root.putChild('stat', GetStat())
    root.putChild('notif', AddNotif(queue=kwargs['qs']['notif']))
    return root


def get_site(*args, **kwargs):
    encoders = [
        server.GzipEncoderFactory()
    ]
    wrapped = resource.EncodingResourceWrapper(get_root_resource(qs=kwargs['qs']), encoders)
    site = server.Site(wrapped)
    return site


class Service(object):
    """Encapsulate HTTP service logic
    """
    def __init__(self, *args, **kwargs):
        self.qs = kwargs['qs']

    def run(self, *args, **kwargs):
        reactor.listenTCP(settings.HTTP_SOCKET['port'], get_site(qs=self.qs))
        #endpoints.serverFromString(reactor, "tcp:8080").listen(site)
        reactor.run(installSignalHandlers=0)


if __name__ == '__main__':
    http_service = Service()
    http_service.run()
