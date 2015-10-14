# encoding: utf-8
'''
Created on 27 août 2015

@author: Bertrand Verdu
'''
from twisted.logger import Logger
from twisted.internet import reactor, endpoints
from twisted.application.internet import StreamServerEndpointService
from twisted.web import server
from twisted.web.resource import Resource

log = Logger()


class Local_server(StreamServerEndpointService):
    '''
    local http server
    '''
    started = False

    def __init__(self):
        '''
        Initialization of UPnP server
        '''
        self.resource = Resource()
        edp = endpoints.serverFromString(reactor, b'tcp:0')
        StreamServerEndpointService.__init__(
            self, edp, server.Site(self.resource))
        self._choosenPort = None

    def privilegedStartService(self):
        r = super(Local_server, self).privilegedStartService()
        self._waitingForPort.addCallback(self.portCatcher)
        return r

    def portCatcher(self, port):
        self._choosenPort = port.getHost().port
#         log.error('Port: {porc}', porc=self._choosenPort)
        return port

    def getPort(self):
        return self._choosenPort

    def startService(self):
        '''
        '''
        super(Local_server, self).startService()
#         log.error('start: {porc}', porc=self._choosenPort)
        self.weburl = "http://%s:" + str(self.getPort())
