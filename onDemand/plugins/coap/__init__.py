'''
Created on 20-09-2015

@author: Maciej Wasilak
'''

import sys

from twisted.internet import reactor
from twisted.python import log
import txthings.coap as coap
import txthings.resource as resource


class Agent():

    def __init__(self, serveraddr='f202::1', observers=[]):
        self.clients = {}
        self.protocol = protocol
        self.remote_addr = serveraddr
        self.observers = observers

    def connect(self, client, obversers=[]):
        if client not in self.clients:
            self.clients.update({client.uid: client})

    def observe(self, clientid, endpoint):
        request = coap.Message(code=coap.GET)
        # Send request to "coap://iot.eclipse.org:5683/obs-large"
        request.opt.uri_path = (endpoint,)
        request.opt.observe = 0x0
        request.remote = (self.remote_addr, coap.COAP_PORT)
        if endpoint not in self.observers:
            self.observers.update(
                {endpoint: {'clients': [clientid], 'value': '', 'numid': 0}})
        elif clientid in self.observers[endpoint]['clients']:
            log.msg('client %s already registered' % clientid)
            self.clients[clientid].callback(self.observers[endpoint]['value'],
                                            endpoint)
            return
        d = protocol.request(request, observeCallback=self.got_notification,
                             observeCallbackArgs=(endpoint))
        d.addCallback(self.check_response, endpoint, {'options': [(6,)]})
        d.addCallback(self.return_value, clientid, endpoint)
        d.addErrback(self.noResponse)

    def check_response(self, response, **kwargs):
        if 'options' in kwargs:
            for opt in kwargs['options']:
                try:
                    val = response.opts.getOption(kwargs['options'][opt[0]])
                except:
                    return (response.payload, -1, None)
                else:
                    return (response.payload, 0, val)
        else:
            return (response.payload, 0, None)

    def return_value(self, payload, clientid, endpoint=None):
        if payload[1] < 0:
            log.msg('error in response')
            if endpoint:
                log.msg('observe not supported, polling...')
                self.polling = True
                self.startpolling()
        else:
            if endpoint:
                if int(payload[2]) > self.obversers[endpoint]['numid']:
                    self.obversers[endpoint]['numid'] = payload[2]
                    self.obversers[endpoint]['value'] = payload[0]
        self.clients[clientid].callback(payload[0], endpoint)

    def got_notification(self, response, endpoint):
        print response.payload

    def noResponse(self, failure):
        print '*** FAILED TO FETCH RESOURCE'
        print failure
        # reactor.stop()

log.startLogging(sys.stdout)

endpoint = resource.Endpoint(None)
protocol = coap.Coap(endpoint)
client = Agent(protocol)

reactor.listenUDP(0, protocol, "::")  # @UndefinedVariable
reactor.run()  # @UndefinedVariable
