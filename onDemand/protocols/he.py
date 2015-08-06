# encoding: utf-8
'''
Created on 21 avr. 2015

@author: babe
'''
import sys
import smbus
from zope.interface import implementer
from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet import interfaces, task, defer, reactor
from twisted.internet.protocol import ClientFactory
from twisted.python import log
from onDemand.protocols import Client, Trigger


@implementer(interfaces.IStreamClientEndpoint)
class Fake_HE_endpoint(object):
    bus = None
    clients = {}

    def __init__(self, reactor, bus_addr, addr, speed):
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
        log.msg('send %s to i2c link' % t)


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
#             log.err('i2c Read IOError')
            self.reading = False
            return
        else:
            self.reading = False
            l = ''.join([chr(code) for code in number]).strip().lstrip('0')
            if l[:-1] in self.clients:
                log.err('i2c: %s' % l)
                self.clients[l[:-1]].lineReceived(l)

    def write(self, msg):
        if self.reading:
            reactor.callLater(0.1, self.write, msg)  # @UndefinedVariable
        self.writing = True
        log.msg(msg)
        t = []
        if len(msg) < 11:
            for n in msg:
                t.append(ord(n))
        else:
            raise Exception('too much data')
        try:
            self.bus.write_i2c_block_data(self.pair, t[0], t[1:])
        except IOError:
            log.err('i2c write IOError')
        finally:
            self.writing = False


class i2cProtocol(LineOnlyReceiver):

    def __init__(self):
        self.__funcs = {}

    def connectionMade(self):
        log.msg('i2c connected')

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


class HE_factory(ClientFactory, Client):

    actions = ('set_target', 'set_status')
    room = 'Home'
    status = False

    def __init__(self, key='00000001', group=0):
#         self.status = False
        self.proto = i2cProtocol()
        self.addr = ''.join((str(key), str(group),))
        self.on_msg = ''.join((str(key), str(group), '1',))
        self.off_msg = ''.join((str(key), str(group), '0',))
        self.proto.factory = self

    def doStart(self):
        self.register_callback(self.addr, self.x_set_status)

    def register_callback(self, name, func):
        self.proto.addCallback(name, func)

    def x_get_room(self):
        return self.room

    def x_set_target(self, value):
#         log.msg(value)
        if value is True:
            self.proto.send_on()
        else:
            self.proto.send_off()
        self.status = value
        self.event(value, 'status')
        log.err('event: %s value: %s' % ('status', value))

    def x_get_target(self):
        return self.status

    def x_get_status(self):
        return self.status

    def x_set_status(self, status):
        log.msg('%s --> %s' % (self.addr, int(status)))
        self.status = status
        self.event(status, 'status')

    def event(self, evt, var):
        pass


class Fake_HE_factory(HE_factory):
    pass


def get_Fake_HE(bus=1, addr='0x04', speed=1, key='00000000', group=0):
    f = HE_factory(key, group)
    e = Fake_HE_endpoint(reactor, bus, addr, speed)
    e.connect(f)
    return e, f


def get_HE(bus=1, addr='0x04', speed=1, key='00000000', group=0):
    f = HE_factory(key, group)
    f.status = False
    e = HE_endpoint(reactor, int(bus), int(addr, 0), speed)
    e.connect(f)
    return e, f

if __name__ == '__main__':
    def show(*args):
        print('triggered: %s' % args)
    log.startLogging(sys.stdout)
    f = HE_factory('16234266', 0)
    f.on_set_target = [Trigger(5, show, 'set')]
    e = Fake_HE_endpoint(reactor, 1, 0x04, 0)
    e.connect(f)
    onoff = False
    for i in range(6):
        reactor.callLater(  # @UndefinedVariable
            i,
            f.set_target,
            not onoff)
        onoff = not onoff
    reactor.run()  # @UndefinedVariable
