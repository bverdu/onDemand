# encoding: utf-8
'''
Created on 17 févr. 2016

@author: Bertrand Verdu
'''

from twisted.logger import Logger
from twisted.internet import defer
from twisted.python import log
import txthings.coap as coap
import txthings.resource as resource


class Agent(object):

    def __init__(self, protocol, serveraddr=b'::1', observers={}):
        self.clients = {}
        self.protocol = protocol
        self.remote_addr = serveraddr
        self.observers = observers
        self.log = Logger()

    def got_notification(self, response, path):
        self.log.debug('Event !')
        if isinstance(response, coap.Message):
            response = response.payload
        if path not in self.observers:
            self.log.debug('bad event')
            return
        if self.observers[path]['value'] != response:
            self.observers[path]['value'] = response
            for c in self.observers[path]['clients']:
                self.clients[c].callback(response, 0, 6, path)

    def connect(self, client, observers=[]):
        if client not in self.clients:
            self.clients.update({client.uid: client})
        t = []
        for obs in observers:
            t.append(self.observe(client.uid, obs))
        return defer.gatherResults(t)

    def get(self, path, observed=None):
        request = coap.Message(code=coap.GET)
        request.opt.uri_path = (path,)
        request.remote = (self.remote_addr, coap.COAP_PORT)
        if observed:
            request.opt.observe = 0x0
            options = {6: None}
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
            if response[1] > -1:
                self.observers[path]['clients'].append(clientid)
            return response[0], response[1], response[2], path

        d = self.get(path, observed=path)
        if path in self.observers:
            if clientid in self.observers[path]['clients']:
                return d
        d.addCallback(record_observer, clientid)
        return d

    def check_response(self, response, **kwargs):
        if 'options' in kwargs:
            for opt in kwargs['options']:
                try:
                    val = response.opt.getOption(opt)
                except:
                    self.log.debug('unable to check option')
                    return (response.payload, -1, None)
                else:
                    return (response.payload, 0, val[0])
            else:
                return (response.payload, 0, None)
        else:
            return (response.payload, 0, None)

    def return_value(self, response, observed=None):
        if response[1] < 0:
            self.log.warn('error in response')
            if observed:
                self.log.warn('observe not supported, polling...')
                self.polling = True
                self.startpolling()
        else:
            if response[2]:
                if not observed:
                    self.log.warn('bad response from server: ' +
                                  'option observe set for a get request')
                    return response
                if observed not in self.observers:
                    self.observers.update(
                        {observed: {'clients': [], 'value': response[0],
                                    'numid': response[2].value}})
                elif int(response[2].value) > self.obversers[
                        observed]['numid']:
                    self.obversers[observed]['numid'] = response[2].value
                    self.got_notification(response[0], observed)
        return response

    def noResponse(self, failure):
        self.log.critical('*** FAILED TO FETCH RESOURCE: {fail}',
                          fail=failure)
        return (None, -1, None)

    def startpolling(self):
        self.log.debug('polling...')


if __name__ == '__main__':

    import sys
    from twisted.internet import reactor
    from twisted.logger import globalLogBeginner, textFileLogObserver

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)

    def show(inst, result, error, opt, arg):
        print("Got result for %s: %s" % (arg, result))
#         reactor.stop()  # @UndefinedVariable

    class Client(object):
        uid = 'test'
        callback = show

        def get_resultlist(self, results):
            for result in results:
                show(self, *result)

    def test(agent):
        #         d = client.get('led')
        test = Client()
        d = agent.connect(test, ['led'])
        d.addCallback(test.get_resultlist)
#         d = client.observe('test', 'led')
#         d.addCallback(show, 'led')

    resource = resource.Endpoint(None)
    protocol = coap.Coap(resource)
    agent = Agent(protocol, b'fd12::1')
    reactor.listenUDP(0, protocol, "::")  # @UndefinedVariable
    reactor.callWhenRunning(test, agent)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
