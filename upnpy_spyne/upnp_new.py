'''
Created on 26 janv. 2015

@author: babe
'''

import time

from spyne_plus.application import Application
from spyne_plus.protocol.soap import Soap11
from spyne_plus.server.twisted import TwistedWebResource
from twisted.application.internet import StreamServerEndpointService
from twisted.internet import endpoints, reactor
from twisted.python import log
from twisted.web import server, static
from twisted.web.error import UnsupportedMethod
from twisted.web.resource import Resource

from upnpy_spyne.device import DeviceIcon
from upnpy_spyne.utils import get_default_v4_address


# import tracemalloc
# from SOAPpy import parseSOAPRPC, buildSOAP
class UPnPService(StreamServerEndpointService):
    '''
    Central class to manage UPnP
    '''
    name = "UPnPServer"

    def __init__(self, device):
        '''
        Initialization of UPnP server
        '''
        self.upnp = UPnP(device)
        self.device = device
        self.upnp.parent = self
        self.site = server.Site(self.upnp)
        edp = endpoints.serverFromString(reactor, "tcp:0")
        StreamServerEndpointService.__init__(self, edp, self.site)
        self._choosenPort = None

    def privilegedStartService(self):
        r = super(UPnPService, self).privilegedStartService()
        self._waitingForPort.addCallback(self.portCatcher)
        return r

    def portCatcher(self, port):
        self._choosenPort = port.getHost().port
        return port

    def getPort(self):
        return self._choosenPort

    def startService(self):
        '''
        '''
        self.device.location = "http://%s:" + str(self.getPort())
        self.device.icons = [
            DeviceIcon(
                'image/png',
                32, 32, 24,
                self.device.getLocation(
                    get_default_v4_address()) + '/pictures/icon.png')
            ]
        log.msg('UPnP Service Started', loglevel='info')


class ServeResource(Resource):
    __slots__ = ['isLeaf', 'data', 'mimetype']
    isLeaf = True

    def __init__(self, data, mimetype):
        Resource.__init__(self)
        self.data = data
        self.mimetype = mimetype

    def render(self, request):
        request.setHeader('Content-Type', self.mimetype)
        log.msg(
            'request method: %s proto = %s' % (
                request.method, request.clientproto),
            loglevel='debug')
        request.clientproto = 'HTTP/1.1'
        log.msg('Rendering Resource: %s' % self.data, loglevel='debug')
        return self.data


class ServiceResource(Resource):
    __slots__ = ['isLeaf', 'service', '__dict__']
    isLeaf = False

    def __init__(self, service):
        Resource.__init__(self)
        self.service = service

    def render(self, request):
        request.setHeader('Content-Type', 'text/xml')
        return self.service.dumps()

    def getChild(self, path, request):
        log.msg('getChild : %s' % request)
        if path == 'event':
            return ServiceEventResource(self.service)

        if path == 'control':
            return ServiceControlResource(self.service)

        log.msg(
            "unhandled request (%s) %s" % (self.service.serviceType, path),
            loglevel='info')
        return Resource()


class ServiceControlResource(TwistedWebResource):
    __slots__ = ['isLeaf', 'service', '__dict__']
    isLeaf = True

    def __init__(self, service):
        self.service = service
        app = Application(self.service,
                          tns=self.service.serviceType,
                          in_protocol=Soap11(validator='lxml'),
                          out_protocol=Soap11())
        TwistedWebResource.__init__(self, app)

    def render(self, request):
        log.msg('control ressource: %s' % request)
        return Resource.render(self, request)


class ServiceEventResource(Resource):
    __slots__ = ['isLeaf', 'service', '__dict__']
    isLeaf = True

    def __init__(self, service):
        Resource.__init__(self)
        self.service = service

    def _parse_nt(self, value):
        if value != 'upnp:event':
            raise ValueError()
        return value

    def _parse_callback(self, value):
        # TODO: Support multiple callbacks as per UPnP 1.1
        if '<' not in value or '>' not in value:
            raise ValueError()
        return value[value.index('<') + 1:value.index('>')]

    def _parse_timeout(self, value):
        if not value.startswith('Second-'):
            raise ValueError()
        return int(value[7:])

    def render(self, request):
        try:
            request.setHeader('Content-Type', 'text/xml')
            return Resource.render(self, request)
        except UnsupportedMethod, e:
            log.msg("unsupported: (%s) %s" % (
                self.service.serviceType,
                request.method),
                loglevel='debug')
            raise e

    def render_SUBSCRIBE(self, request):
        log.msg("(%s) SUBSCRIBE" % self.service.serviceType, loglevel='debug')
#         snapshot = tracemalloc.take_snapshot()
#         top_stats = snapshot.statistics('lineno')
#         print("[ Top 50 ]")
#         for stat in top_stats[:50]:
#             print(stat)
        if request.requestHeaders.hasHeader('sid'):
            # Renew
            sid = getHeader(request, 'sid')
            if sid in self.service.subscriptions:
                for subscription in self.service.subscriptions[sid]:
                    subscription.last_subscribe = time.time()
                    subscription.expired = False
#                 self.service.subscriptions[sid].last_subscribe = time.time()
#                 self.service.subscriptions[sid].expired = False
                log.msg("(%s) Successfully renewed subscription" %
                        self.service.serviceType, loglevel='debug')
            else:
                log.msg("(%s) Received invalid subscription renewal" %
                        self.service.serviceType, loglevel='debug')
        else:
            # New Subscription
            #  nt = self._parse_nt(getHeader(request, 'nt'))
            callback = self._parse_callback(getHeader(request, 'callback'))
            timeout = self._parse_timeout(getHeader(request, 'timeout', False))
            log.msg(
                "New subscription: (%s) %s %s" % (
                    self.service.serviceType, callback, timeout),
                loglevel='info')
            responseHeaders = self.service.subscribe(callback, timeout)
            if responseHeaders is not None and type(responseHeaders) is dict:
                for name, value in responseHeaders.items():
                    request.setHeader(name, value)
                return ''
            else:
                log.err("(%s) SUBSCRIBE FAILED" % self.service.serviceType)

    def render_UNSUBSCRIBE(self, request):
        log.msg("(%s) UNSUBSCRIBE" % self.service.serviceType, loglevel='info')

        if request.requestHeaders.hasHeader('sid'):
            # Cancel
            sid = getHeader(request, 'sid')
            if sid in self.service.subscriptions:
                for i, subscription in enumerate(self.service.subscriptions[sid]):
                    self.service.subscriptions[sid][i].expired = True
                log.msg(
                    "(%s) Successfully unsubscribed" %
                    self.service.serviceType,
                    loglevel='debug')
            else:
                log.msg(
                    "(%s) Received invalid UNSUBSCRIBE request" %
                    self.service.serviceType,
                    loglevel='debug')
        else:
            log.msg("(%s) Received invalid UNSUBSCRIBE request" %
                    self.service.serviceType,
                    loglevel='debug')
        return ''


class UPnP(Resource):
    __slots__ = ['isLeaf', 'device', 'running', '__dict__']
    isLeaf = False

    def __init__(self, device):
        """UPnP Control Server
        :type device: Device
        """
        Resource.__init__(self)
        self.device = device
        self.running = False
        self.putChild("pictures", static.File(device.datadir + 'icons'))

    def stop(self):
        if not self.running:
            return
        log.msg("Stopping UPnP Service", loglevel='info')
        self.site_port.stopListening()
        self.running = False

    def getChild(self, path, request):
        # Hack to fix twisted not accepting absolute URIs
        #   path, request = twisted_absolute_path(path, request)
        log.msg("upnp request: path:%s Request:%s" % (path, request),
                loglevel='debug')
        if path == '':
            return ServeResource(self.device.dumps(), 'text/xml')

        for service in self.device.services:
            if path == service.serviceUrl:
                return ServiceResource(service)

        log.msg("unhandled request %s" % path, loglevel='debug')
        return Resource()


def getHeader(request, name, required=True, default=None):
    result = request.requestHeaders.getRawHeaders(name)
    if len(result) != 1:
        if required:
            raise KeyError()
        else:
            return default
    return result[0]


class UpnPClient(object):
    pass
