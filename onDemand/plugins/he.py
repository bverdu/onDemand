# encoding: utf-8
'''
Home Easy plugin

Created on 21 avr. 2015

@author: Bertrand Verdu
'''
import sys
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.python import log
from . import Client
from onDemand.protocols.i2c import i2cProtocol, HE_endpoint, Fake_HE_endpoint


class HE_factory(ClientFactory, Client):

    actions = ('set_target', 'set_status')
    room = 'Home'

    def __init__(self, key='00000001', group=0, net_type='lan'):
        self.status = False
        self.init = True
        self.proto = i2cProtocol()
        self.addr = ''.join((str(key), str(group),))
        self.on_msg = ''.join((str(key), str(group), '1',))
        self.off_msg = ''.join((str(key), str(group), '0',))
        self.proto.factory = self

    def doStart(self):
        self.register_callback(self.addr, self.r_set_status)

    def register_callback(self, name, func):
        self.proto.addCallback(name, func)

    def event(self, evt, var):
        pass

    '''
    Remote functions
    '''

    def r_get_room(self):
        return self.room

    def r_set_target(self, value):
        print('**************************************************')
        if (value is not self.status) or self.init:
            self.init = False
            if value is True:
                self.proto.send_on()
            else:
                self.proto.send_off()
            self.status = value
            self.event(value, 'status')
            log.err('event: %s value: %s' % ('status', value))

    def r_get_target(self):
        return self.status

    def r_get_status(self):
        return self.status

    def r_set_status(self, status):
        self.init = False
        if status is not self.status:
            log.msg('%s --> %s' % (self.addr, int(status)))
            self.status = status
            self.event(status, 'status')


class Fake_HE_factory(HE_factory):
    pass


def get_Fake_HE(bus=1, addr='0x04', speed=1, key='00000000', group=0, net_type='lan'):
    f = HE_factory(key, group, net_type=net_type)
    e = Fake_HE_endpoint(reactor, bus, addr, speed)
    e.connect(f)
    return e, f


def get_HE(bus=1, addr='0x04', speed=1, key='00000000', group=0, net_type='lan'):
    f = HE_factory(key, group, net_type=net_type)
    f.status = False
    e = HE_endpoint(reactor, int(bus), int(addr, 0), speed)
    e.connect(f)
    return e, f

if __name__ == '__main__':
    from . import Trigger

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
