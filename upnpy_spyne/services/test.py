# encoding: utf-8
'''
Created on 17 mars 2015

@author: babe
'''
import sys
from spyne.client import Service
from spyne.client import RemoteProcedureBase
from spyne.client import ClientBase
from spyne.application import Application
from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer
from spyne.model.primitive import Unicode
from spyne.model.complex import Iterable
from spyne.protocol.soap import Soap11
from spyne.server.twisted import TwistedWebResource
from spyne.client.twisted import TwistedHttpClient, _Producer, _Protocol
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web import error as werror
from twisted.python import log
from upnpy_spyne.services.templates import contentdirectory
from upnpy_spyne.utils import didl_decode

test_ok = '''<?xml version="1.0" encoding="utf-8" standalone="yes"?><s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><u:Browse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1"><ObjectID>0</ObjectID><BrowseFlag>BrowseDirectChildren</BrowseFlag><Filter>*</Filter><StartingIndex>0</StartingIndex><RequestedCount>16</RequestedCount><SortCriteria></SortCriteria></u:Browse></s:Body></s:Envelope>'''
class MyClass(ServiceBase):
    '''
    classdocs
    '''
    def __new__(self):
        print('new')

    def __init__(self):
        print('init !')
        super(MyClass, self).__init__()

    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def say_hello(ctx, name, times):  # @NoSelf
        pass
#         for i in range(times):
#             yield 'Hello, %s' % name


class titi(MyClass):
    player = ('do')

    def __init__(self):
        print('toto')
        self.player = 're'

    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def say_hello(ctx, name, times):  # @NoSelf
        for i in range(times):  # @UnusedVariable
            yield 'Hello, %s' % name


application = Application([titi],
                          tns='spyne.examples.hello',
                          in_protocol=Soap11(validator='lxml'),
                          out_protocol=Soap11())


class Custom_RemoteProcedure(RemoteProcedureBase):
    def __call__(self, *args, **kwargs):
        # there's no point in having a client making the same request more than
        # once, so if there's more than just one context, it's rather a bug.
        # The comma-in-assignment trick is a pedantic way of getting the first
        # and the only variable from an iterable. so if there's more than one
        # element in the iterable, it'll fail miserably.
        self.ctx, = self.contexts
        self.get_out_object(self.ctx, args, kwargs)
        self.get_out_string(self.ctx)
#         self.ctx.out_string[0] = self.ctx.out_string[0].replace('tns:', '').replace('tns=', '')
#         self.ctx.out_string[0] = test_ok
        self.ctx.in_string = []
        header = {'User-Agent': ['onDemand Controller']}
        if self.ctx.out_header is not None:
            if 'Soapaction' in self.ctx.out_header:
                self.ctx.out_header.update(
                    {'Soapaction': [
                        '"' + self.ctx.out_header['Soapaction'][0] +
                        '#' + self.ctx.method_request_string + '"']})
            header.update(self.ctx.out_header)
        agent = Agent(reactor)
        d = agent.request(
            'POST', self.url,
            Headers(header),
            _Producer(self.ctx.out_string)
        )

        def _process_response(_, response):
            # this sets ctx.in_error if there's an error, and ctx.in_object if
            # there's none.
            print(response.code)
            self.get_in_object(self.ctx)

            if self.ctx.in_error is not None:
                log.err(self.ctx.in_error)
#                 raise self.ctx.in_error
            elif response.code >= 400:
                log.err(werror.Error(response.code))
            return self.ctx.in_object

        def _cb_request(response):
            p = _Protocol(self.ctx)
            response.deliverBody(p)
            return p.deferred.addCallback(_process_response, response)

        d.addCallback(_cb_request)
        return d

class Client(ClientBase):
    def __init__(self, url, app):
        super(Client, self).__init__(url, app)
        self.service = Service(Custom_RemoteProcedure, url, app)


def show(res):
    log.msg('result: %s' % res)
    print(dir(res))
    if res:
        for i, r in enumerate(res):
            print('%s --> %s' % (i, r))
        for item in didl_decode(res.Result):
            print(item)
    reactor.callLater(2, reactor.stop)  # @UndefinedVariable

if __name__ == '__main__':
    log.startLogging(sys.stdout)
    def test():
        client = Client(
            'http://192.168.0.134:58645/dev/106c66cc-d1be-6466-0000-00000156d879/svc/upnp-org/ContentDirectory/action', Application(
                [contentdirectory.ContentDirectory],
               contentdirectory.ContentDirectory.tns,
                in_protocol=Soap11(),
                out_protocol=Soap11()))
        client.set_options(
            out_header={
                'Content-Type': ['text/xml;charset="utf-8"'],
                'Soapaction': [contentdirectory.ContentDirectory.tns]})
        d = client.service.Browse('0', 'BrowseDirectChildren', '*', 0, 0, '')
        d.addCallback(show)
#         client2 = od_TwistedHttpClient('http://127.0.0.1:8000', application)
#         d= client2.service.say_hello('word', 5)
#         d.addCallback(show)
#     resource = TwistedWebResource(application)
#     site = Site(resource)
#     reactor.listenTCP(8000, site, interface='0.0.0.0')  # @UndefinedVariable
    
    reactor.callWhenRunning(test)  # @UndefinedVariable
#     print(client.service.say_hello('word', 5))
    reactor.run()  # @UndefinedVariable
