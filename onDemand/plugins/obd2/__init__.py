# encoding: utf-8

'''
Created on 16 march. 2016

@author: Bertrand Verdu
'''
from collections import OrderedDict
from twisted.internet import reactor
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.logger import Logger
from onDemand.plugins import Client

EVENTS = ['']


class Obd_Factory(ReconnectingClientFactory, Client):
    proto = None

    def __init__(self):
        self.log = Logger()
        self.attempts = 0
        self.descriptor = None
        self.generate_service()
        self.event = None
        self.initialized = False
        self.update_config = None

    def generate_service(self):
        if self.proto is None:
            reactor.callLater(.2, self.generate_service)  # @UndefinedVariable
            return
        if not self.proto.obdconnected:
            if self.attempts > 20:
                self.log.error("Unable to connect to ECU, aborting")
                self.descriptor = ''
            else:
                self.attempts += 1
                reactor.callLater(.2,  # @UndefinedVariable
                                  self.generate_service)
            return
        self.log.debug("Connected to ECU, generating services list")
        self.state_variables = [('ObdResponse', 'string')]
        self.actions = OrderedDict()
        for c in self.proto.supported_commands.itervalues():
            self.actions.update(
                {c.name: [(c.name + '_Result', 'out', 'ObdResponse',)]})
            #
            #  self.log.debug(c.name)
        self.initialized = True
        if self.update_config is not None:
            self.update_config()

    def watch(self, interval):
        pass

    def __getattr__(self, attr):
        if attr.startswith('r_'):
            if attr == 'r_Watch':
                return self.watch
            return Call_Proxy(attr[2:], self.proto)
        else:
            raise AttributeError


class Call_Proxy(object):

    def __init__(self, cmd_str, proto):
        self.command = cmd_str
        self.proto = proto

    def __call__(self, *args):
        return self.proto.call(self.command)


def get_Obd(port=b'/dev/pts/3', **kwargs):
    from twisted.internet.serialport import SerialPort
    from base import BaseProtocol
    endpoint = BaseProtocol()
    f = Obd_Factory()
    endpoint.connect(f)

    SerialPort(endpoint, port, reactor)

    return endpoint, f

if __name__ == '__main__':
    import sys
    from twisted.logger import globalLogBeginner, textFileLogObserver

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)

    e, f = get_Obd()

    def test():
        d = f.r_DISTANCE_W_MIL()
        d.addCallback(show, 'Kilométrage')
        reactor.callLater(20, reactor.stop)  # @UndefinedVariable

    def show(evt, prefix):
        print("%s : %s" % (prefix, evt))

    reactor.callWhenRunning(test)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
