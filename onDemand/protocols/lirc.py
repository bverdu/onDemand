'''
Created on 8 nov. 2014

@author: babe
'''
from twisted.python import log
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import defer, reactor
import time


class LircdProtocol(LineReceiver):
    __slots__ = ['__repeat_delay',
                 '__funcs',
                 'delimiter',
                 '__current',
                 '__term',
                 '__dict__']

    def __init__(self, repeat_delay):
        '''
        repeat_delay: amount of time the same key is repeated\n
         to consider it is a repeat
        '''
        self.__repeat_delay = float(repeat_delay)
        self.__funcs = {}
        self.delimiter = "\n"
        self.__current = ""
        self.__term = 0.00

    def lineReceived(self, line):
        try:
            (code, pos, name, remote) = line.split(" ")
            pos = int(pos, 16)
            code = int(code, 16)
        except:
            return
        t = time.time()
        called = name + remote
        try:
            call = self.__funcs[called]
        except:
            return
        else:
            if call['repeat']:
                self.__current = name + remote
                call['fct']()
            elif called != self.__current:
                    self.__term = t + self.__repeat_delay
                    self.__current = name + remote
                    call['fct']()
            elif t > self.__term:
                self.__term = t + self.__repeat_delay
                call['fct']()

    def addCallback(self, name, func, repeat=False):
        self.__funcs[name] = {'fct': func, 'repeat': repeat}


class LircdFactory(ReconnectingClientFactory):
    def __init__(self, delay, simul=False):
        self.simul = simul
        self.proto = LircdProtocol(delay)

    def buildProtocol(self, addr):
        return self.proto

    def addCallback(self, name, func, repeat=False):
        self.proto.addCallback(name, func, repeat)

    def send(self, command, transmitter, simul=False):
        def simulate(d):
            log.msg('IRsend: %s %s ' % (transmitter, command), loglevel='info')
            d.callback(None)
        if self.simul or simul:
            d = defer.Deferred()
            reactor.callLater(0.1, simulate, d)  # @UndefinedVariable
            return d
        else:
            log.msg('IRsend:%s %s ' % (transmitter, command), loglevel='info')
            # double the ir signal for safety
            reactor.callLater(  # @UndefinedVariable
                0.1,
                self.proto.sendLine,
                *('SEND_ONCE %s %s' % (transmitter, command),))
            self.proto.sendLine('SEND_ONCE %s %s' % (transmitter, command))

if __name__ == '__main__':
    def print_code(name=''):
        print('intercepted: %s' % name)
    lircd = LircdFactory(0.5)
    lircd.addCallback('KEY_RIGHT'+'devinput', print_code)
    reactor.connectUNIX("/var/run/lirc/lircd", lircd)  # @UndefinedVariable
    lircemitter = LircdFactory(0.5)
    reactor.connectUNIX(  # @UndefinedVariable
        "/var/run/lirc/lircd_rpi",
        lircemitter)
    for i in range(5):
        reactor.callLater(  # @UndefinedVariable
            i,
            lircemitter.send,
            *('KEY_POWER', 'src-tm2',))
    print('ready')
    reactor.run()  # @UndefinedVariable
