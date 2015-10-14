# encoding: utf-8
'''
Created on 30 août 2015

@author: Bertrand Verdu
'''
import smbus
from zope.interface import implementer
from twisted.logger import Logger
from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet import interfaces, task, defer, reactor


@implementer(interfaces.IStreamClientEndpoint)
class Fake_HE_endpoint(object):
    bus = None
    clients = {}

    def __init__(self, reactor, bus_addr, addr, speed):
        self.log = Logger()
        self.reactor = reactor
        self.bus_addr = bus_addr
        self.pair = addr
        self.speed = speed
        self.running = False

    def connect(self, clientFactory):
        proto = clientFactory.proto
        proto.transport = self
        if clientFactory.addr not in self.clients:
            self.clients.update({clientFactory.addr: proto})
        if not self.bus:
            r = task.LoopingCall(self.check)
            r.start(20)
        clientFactory.doStart()
        return defer.succeed(None)

    def check(self):
        if not self.running:
            for client in self.clients.values():
                client.connectionMade()
            self.running = True
            self.bus = True
        l = '1623426601'
        ll = '3344556600'
        if l[:-1] in self.clients:
            self.clients[l[:-1]].lineReceived(l)
        if ll[:-1] in self.clients:
            self.clients[ll[:-1]].lineReceived(ll)

    def write(self, msg):
        t = []
        if len(msg) < 11:
            for n in msg:
                t.append(ord(n))
        else:
            raise Exception('too much data')
        self.log.debug('send %s to i2c link' % t)


@implementer(interfaces.IStreamClientEndpoint)
class HE_endpoint(object):
    bus = None
    clients = {}

    def __init__(self, reactor, bus_addr, addr, speed):
        self.reactor = reactor
        self.bus_addr = bus_addr
        self.pair = addr
        self.speed = speed
        self.running = False
        self.writing = False
        self.reading = False

    def connect(self, clientFactory):
        proto = clientFactory.proto
        proto.transport = self
        if clientFactory.addr not in self.clients:
            self.clients.update({clientFactory.addr: proto})
        if not self.bus:
            try:
                self.bus = smbus.SMBus(int(self.bus_addr))
            except IOError:
                return defer.fail(IOError())
            else:
                r = task.LoopingCall(self.check)
                r.start(0.2)
        clientFactory.doStart()
        return defer.succeed(None)

    def check(self):
        if not self.running:
            for client in self.clients.values():
                client.connectionMade()
            self.running = True
        if self.writing:
            return
        self.reading = True
        try:
            first = self.bus.read_byte(self.pair)
            if first == 255:
                self.reading = False
                return
            number = [first]
            for i in range(9):
                number.append(self.bus.read_byte(self.pair))
#             number = self.bus.read_i2c_block_data(self.pair, 255, 10)
        except IOError:
            # log.err('i2c Read IOError')
            self.reading = False
            return
        else:
            self.reading = False
            l = ''.join([chr(code) for code in number]).strip().lstrip('0')
            if l[:-1] in self.clients:
                self.log.error('i2c: %s' % l)
                self.clients[l[:-1]].lineReceived(l)

    def write(self, msg):
        if self.reading:
            reactor.callLater(0.1, self.write, msg)  # @UndefinedVariable
        self.writing = True
        self.log.debug(msg)
        t = []
        if len(msg) < 11:
            for n in msg:
                t.append(ord(n))
        else:
            raise Exception('too much data')
        try:
            self.bus.write_i2c_block_data(self.pair, t[0], t[1:])
        except IOError:
            self.log.error('i2c write IOError')
        finally:
            self.writing = False


class i2cProtocol(LineOnlyReceiver):

    def __init__(self):
        self.log = Logger()
        self.__funcs = {}

    def connectionMade(self):
        self.log.debug('i2c connected')

    def lineReceived(self, line):
        line = line.strip()
        called = line[:9].lstrip('0')
        onoff = bool(int(line[-1]))
        try:
            call = self.__funcs[called]
        except:
            return
        else:
            call(onoff)

    def send_on(self):
        self.transport.write(self.factory.on_msg)

    def send_off(self):
        self.transport.write(self.factory.off_msg)

    def addCallback(self, name, func):
        self.__funcs[name] = func

    def remCallback(self, name):
        try:
            del self.__funcs[name]
        except KeyError:
            return

if __name__ == '__main__':
    pass
