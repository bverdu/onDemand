# encoding: utf-8
'''
Created on 17 févr. 2016

@author: Bertrand Verdu
'''

from twisted.internet import reactor
from twisted.python import log
import txthings.coap as coap
import txthings.resource as resource


class Agent(object):

    def __init__(self, protocol, serveraddr=b'::1', observers={}):
        self.clients = {}
        self.protocol = protocol
        self.remote_addr = serveraddr
        self.observers = observers

    def got_notification(self, response, path):
        print('Event !!!')
        if self.obversers[path]['value'] != response:
            self.obversers[path]['value'] = response
            for c in self.observers[path]['clients']:
                self.clients[c].callback(response, path, 0)

    def connect(self, client, obversers=[]):
        if client not in self.clients:
            self.clients.update({client.uid: client})

    def get(self, path, observed=None):
        request = coap.Message(code=coap.GET)
        request.opt.uri_path = (path,)
        request.remote = (self.remote_addr, coap.COAP_PORT)
        if observed:
            request.opt.observe = 0x0
            options = {'options': [(6,)]}
        else:
            request.opt.observe = None
            options = {}
        d = self.protocol.request(request,
                                  observeCallback=self.got_notification,
                                  observeCallbackArgs=(observed,))
        d.addCallback(self.check_response, options=options)
        d.addErrback(self.noResponse)
        d.addCallback(self.return_value, observed)
        return d

    def observe(self, clientid, path):
        def record_observer(response, clientid):
            if response[2] > -1:
                self.observers[response[1]]['clients'].append(clientid)
            return response

        d = self.get(path, observe=path)
        if path in self.observers:
            if clientid in self.observers[path]['clients']:
                return d
        d.addCallback(record_observer, clientid)
        return d

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
        else:
            return (response.payload, 0, None)

    def return_value(self, payload, observed=None):
        if payload[1] < 0:
            log.msg('error in response')
            if observed:
                log.msg('observe not supported, polling...')
                self.polling = True
                self.startpolling()
        else:
            if payload[2]:
                if not observed:
                    print('bad response from server: ' +
                          'option observe set for a get request')
                    return payload
                if observed not in self.observers:
                    self.observers.update(
                        {observed: {'clients': [], 'value': payload[0],
                                    'numid': payload[2]}})
                elif int(payload[2]) > self.obversers[observed]['numid']:
                    self.obversers[observed]['numid'] = payload[2]
                    self.got_notification(payload[0], observed)
        return payload

    def noResponse(self, failure):
        print '*** FAILED TO FETCH RESOURCE'
        print failure
        return (None, -1, None)

if __name__ == '__main__':
    def show(result, arg):
        print('Got result for %s: %s , option= %s, error code=%d'
              % (arg, result[0], result[2], result[1]))
        reactor.stop()  # @UndefinedVariable

    def test(client):
        d = client.get('led')
        d.addCallback(show, 'led')

    resource = resource.Endpoint(None)
    protocol = coap.Coap(resource)
    client = Agent(protocol, b'fd12:3456:789a:1::1')
    reactor.listenUDP(0, protocol, "::")  # @UndefinedVariable
    reactor.callWhenRunning(test, client)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
