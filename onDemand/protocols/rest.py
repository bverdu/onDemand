# encoding: utf-8
# !/usr/bin/python2.7
'''
Created on 14 août 2015

@author: Bertrand Verdu
'''
import json
# from pprint import pformat
from cStringIO import StringIO

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent,\
    RedirectAgent, FileBodyProducer, HTTPConnectionPool
from twisted.web.http_headers import Headers
from twisted.web.http import urlparse
from twisted.logger import Logger


class RestHandle(Protocol):

    def __init__(self, finished, event_handler=None):
        self.event_handler = event_handler
        self.finished = finished
        self.buf = b''
        self.state = b''

    def dataReceived(self, bytes_):
        if '\n' in bytes_:
            lines = bytes_.split('\n')
            if len(lines) > 2:
                for line in lines:
                    if len(line) > 0:
                        self.process_line(self.buf + line)
                self.buf = b''
            else:
                self.process_line(self.buf + line[0])
                self.buf = line[1]
        else:
            self.buf += bytes_

    def process_line(self, line):
        if line.startswith(b'event'):
            event = ''.join(line.split('event: ')[1:])
            self.state = event

        elif line.startswith(b'data'):
            if self.state in ('put', 'patch'):
                data = ''.join(line.split('data: ')[1:])
                n = json.loads(data)
                if self.event_handler:
                    self.event_handler(n)

    def connectionLost(self, reason):
        #         print 'Finished receiving body:', reason.getErrorMessage()
        if len(self.buf) > 0:
            self.finished.callback(json.loads(self.buf))
        else:
            self.finished.callback({'reason': reason.getErrorMessage()})


class RestCall(object):

    def __init__(self, obj, name):
        self.name = name
        self.con = obj

    def __call__(self, *args, **kwargs):
        path = self.name
        if len(args) > 0:
            path = '/'.join((self.name, args[0]))
        if 'path' in kwargs:
            path = '/'.join((self.name, kwargs['path']))
            del kwargs['path']
        if len(kwargs) > 0:
            return self.con.request(method='PUT',
                                    path=path,
                                    body=kwargs)
        else:
            return self.con.request(path=path)


class Rest(object):

    def __init__(
            self,
            host='https://developer-api.nest.com',
            token=None,
            event_handler=None,
            net_type='lan'):
        self.log = Logger()
        self.host = host
        self.token = token
        self.event_handler = event_handler
        self.pool = HTTPConnectionPool(reactor, persistent=True)
        self.loc = None
        self.reconnect = False
        self.fail_count = 0
        if event_handler:
            self.reconnect = True
            d = self.request(headers={'User-Agent': ['onDemand Rest Client'],
                                      'Accept': ['text/event-stream']})
            d.addCallback(self.on_disconnect)

    def __getattr__(self, name):
        try:
            super(Rest, self).__getattr__(name)
        except AttributeError:
            return RestCall(self, name)

    def on_disconnect(self, reason):
        if not reason:
            reason = {'reason': 'no_message'}
        self.log.critical(
            'disconnected: {reason}', reason=reason['reason'])
        if self.fail_count > 10:
            self.log.error('Max error count reached, aborting connection')

        def test_connectivity(count):
            if self.fail_count == count:
                self.fail_count = 0

        self.fail_count += 1
        c = self.fail_count
        reactor.callLater(10, test_connectivity, c)  # @UndefinedVariable
        if self.reconnect:
            d = self.request(headers={'User-Agent': ['onDemand Rest Client'],
                                      'Accept': ['text/event-stream']})
            d.addCallback(self.on_disconnect)

    def request(self, method='GET',
                path='',
                headers={'User-Agent': ['onDemand/1.0 (Rest_Client)'],
                         'Accept': ['application/json']},
                body=None):

        data = None
        if self.loc:
            host = '/'.join((self.loc, path))
        else:
            host = '/'.join((self.host, path))
        if self.token:
            host += '?auth=' + self.token
        if body:
            headers.update({'Content-Type': ['application/json']})
            data = FileBodyProducer(StringIO(json.dumps(body)))
        agent = RedirectAgent(Agent(reactor, pool=self.pool))
        d = agent.request(method, host, Headers(headers), data)

        def cbFail(fail):

            if hasattr(fail.value, 'response'):
                if hasattr(fail.value.response, 'code'):
                    if fail.value.response.code == 307:
                        loc = fail.value.response.headers.getRawHeaders(
                            'location')
                        new = urlparse(loc[0])
                        newhost = '://'.join((new.scheme, new.netloc))
                        if newhost == self.host:
                            self.loc = None
                        else:
                            self.loc = newhost
                        self.log.debug('redirect: %s' % self.loc)
                        data = FileBodyProducer(StringIO(json.dumps(body)))
                        d = agent.request(
                            method, loc[0], Headers(headers), data)
                        d.addCallbacks(cbRequest, cbFail)
                        return d
                    elif fail.value.response.code == 404 and self.loc:
                        self.loc = None
                        host = '/'.join((self.host, path))
                        if self.token:
                            host += '?auth=' + self.token
                        d = self.request(method, host, Headers(headers), body)
                        d.addCallbacks(cbRequest, cbFail)
                        return d
                else:
                    print(dir(fail.value))
                    print(fail.value.message)
                    print(fail.value.args)

            self.log.error('unhandled failure: %s -- %s' % (
                fail.value.message, fail.value))

        def cbRequest(response):
            #  print 'Response version:', response.version
            #  print 'Response code:', response.code
            #  print 'Response phrase:', response.phrase
            #  print 'Response headers:'
            #  print pformat(list(response.headers.getAllRawHeaders()))
            finished = Deferred()
            response.deliverBody(RestHandle(finished, self.event_handler))
            return finished
        d.addCallbacks(cbRequest, cbFail)
        return d


if __name__ == '__main__':

    import sys
    from twisted.logger import globalLogBeginner, textFileLogObserver

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)

    cl = True
#     log.startLogging(sys.stdout)
    log = Logger()

    def set_temp(obj):
        temp = obj.devices(
            path='thermostats/o4WARbb6TBa0Z81uC9faoLuE3_EunExt',
            target_temperature_c=23)
        temp.addCallback(result, 'temp set_request')

    def result(data, prefix=''):
        log.info('{prefix} request result: {data}', prefix=prefix, data=data)
#         reactor.stop()  # @UndefinedVariable

    def event(data):
        log.info('event data: {data}', data=data)
        global cl
        if cl:
            cl = False
            reactor.callLater(5, set_temp, napi)  # @UndefinedVariable
            reactor.callLater(20, reactor.stop)  # @UndefinedVariable
    try:
        from onDemand.test_data import nest_token
    except:
        nest_token = 'PUT YOUR TOKEN HERE'
    napi = Rest(host='https://developer-api.nest.com',
                token=nest_token,
                event_handler=event)

    structures = napi.structures()
    structures.addCallback(result, 'structures')
    devices = napi.devices('thermostats')
    devices.addCallback(result, 'devices')
    #     urls = napi.urls()
    #     urls.addCallback(result, 'urls')
    temp = napi.devices(
        'thermostats/o4WARbb6TBa0Z81uC9faoLuE3_EunExt',
        target_temperature_c=21)
    temp.addCallback(result, 'temp set_request')
    reactor.run()  # @UndefinedVariable
