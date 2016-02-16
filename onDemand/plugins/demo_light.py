# encoding: utf-8

'''
Created on 19 nov. 2015

@author: Bertrand Verdu
'''

from twisted.internet.protocol import ReconnectingClientFactory
from twisted.logger import Logger
from onDemand.plugins.zigbee import ZigBee
from onDemand.plugins import Client


ENDPOINT = 'zigbee'


class Demo_light_factory(ReconnectingClientFactory, Client):

    def __init__(self, long_address=b'\x00\x00\x00\x00\x00\x00\xFF\xFF',
                 address=b'\xFF\xFE', pin=0,
                 api_level=1, net_type=None, stateless=True):
        self.long_address = long_address.decode('hex')
        self.address = address
        self._pin = pin
        self.pin = 'dio-' + bytes(pin)
        self.status = False
        self.proto = None
        self.log = Logger()
        self.callback = self.receive
        self.stateless = stateless
        self.events = {'Status': self.set_status}

    '''
    Remote functions
    '''

    def r_set_target(self, value):

        if value is not self.status:
            if value is True:
                self.proto.remote_at(dest_addr_long=self.long_address,
                                     command=b'D%d' % self._pin,
                                     parameter=b'\x05')
            else:
                self.proto.remote_at(dest_addr_long=self.long_address,
                                     command=b'D%d' % self._pin,
                                     parameter=b'\x04')

            if self.stateless:
                self.status = value
                self.event(value, 'status')

    def r_get_target(self):
        return self.status

    def r_get_status(self):
        return self.status

    def check_status(self, status):
        if status is not self.status:
            self.set_status(status)

    def set_status(self, status):
        self.log.debug('%r --> %s' % (self.long_address,
                                      'jour!' if status else 'nuit!'))
        self.status = status
        self.event(status, 'status')

    def receive(self, data):
        if 'samples' in data:
            for sample in data['samples']:
                if self.pin in sample:
                    self.check_status(sample[self.pin])
        elif 'parameter' in data:
            for sample in data['parameter']:
                if self.pin in sample:
                    self.check_status(sample[self.pin])


def get_Demo_light(device=b'/dev/ttyACM0', pin=0, api_level=1,
                   long_address=b'000000000000FFFF',
                   address=b'\xFF\xFE', net_type='lan',  stateless=True, **kwargs):
    from twisted.internet import reactor
    from twisted.internet.serialport import SerialPort
    f = Demo_light_factory(long_address, address, pin, net_type, stateless)
    endpoint = ZigBee(callback=f.receive,
                      escaped=True if (api_level > 1) else False)
    endpoint.connect(f)
#     f.proto = endpoint

    SerialPort(endpoint, device, reactor, **kwargs)

    return endpoint, f

if __name__ == '__main__':
    import sys
    from twisted.internet import reactor
    from twisted.logger import globalLogBeginner, textFileLogObserver

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)

    e, f = get_Demo_light(pin=2, api_level=2, baudrate=57600)

    def test():
        if f.proto.connected:
            f.r_set_target(True)
            reactor.callLater(5, f.r_set_target, False)  # @UndefinedVariable
            reactor.callLater(10, reactor.stop)  # @UndefinedVariable

    def event(evt, prefix):
        print(b'received %s Event : %s' % (prefix, evt))

    f.event = event
    reactor.callWhenRunning(test)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
