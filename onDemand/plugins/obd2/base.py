# encoding: utf-8
'''
Created on 16 mars 2016

@author: Bertrand Verdu
'''
import re
from collections import OrderedDict
from twisted.internet import defer, reactor, task
from twisted.logger import Logger
from onDemand.protocols.serial import serialBytesProtocol
import protocols
from utils import numBitsSet, constrainHex
from commands import commands


class BaseProtocol(serialBytesProtocol):

    SUPPORTED_PROTOCOLS = {
        # "0" : None, # automatic mode
        "1": protocols.SAE_J1850_PWM,
        "2": protocols.SAE_J1850_VPW,
        "3": protocols.ISO_9141_2,
        "4": protocols.ISO_14230_4_5baud,
        "5": protocols.ISO_14230_4_fast,
        "6": protocols.ISO_15765_4_11bit_500k,
        "7": protocols.ISO_15765_4_29bit_500k,
        "8": protocols.ISO_15765_4_11bit_250k,
        "9": protocols.ISO_15765_4_29bit_250k,
        "A": protocols.SAE_J1939
    }

    def __init__(self, callback=None, error_callback=None):

        serialBytesProtocol.__init__(self)
        if callback:
            self.callbacks = [callback]
        else:
            self.callbacks = []
        self.setRawMode()
        self.log = Logger()
        self.requests = {}
        self.command_id = 0
        self.buffer = None
        self.wait = []
        self.ready = False
        self.commands = []
        self.obd_proto = None
        self.primary_ecu = None
        self.obdconnected = False
        self.managed = True
        self.supported_commands = OrderedDict()

    def _find_primary_ecu(self, messages):
        """
            Given a list of messages from different ECUS,
            (in response to the 0100 PID listing command)
            choose the ID of the primary ECU
        """
        if len(messages) == 0:
            return None
        elif len(messages) == 1:
            #  print(sum([numBitsSet(b) for b in messages[0].data_bytes]))
            return messages[0].tx_id
        else:
            best = 0
            tx_id = None
            for message in messages:
                if message.tx_id == self.obd_proto.PRIMARY_ECU:
                    return self.obd_proto.PRIMARY_ECU
                bits = sum([numBitsSet(b) for b in message.data_bytes])
                if bits > best:
                    best = bits
                    tx_id = message.tx_id
            return tx_id

    @defer.inlineCallbacks
    def connectionMade(self):
        info = yield self._call('ATZ', force=True)
        for l in info:
            if l == 'ATZ':
                continue
            self.log.debug('Device type: %s' % l)
        init = ('ATE0', 'ATH1', 'ATL0', 'ATAL', 'ATTPAA', '0100')
        for cmd in init:
            result = yield self._call(cmd)
            for l in result:
                if l == cmd:
                    continue
                else:
                    self.log.debug('%s: %s' % (cmd, l))
        proto = yield self._call('ATDPN')
        if len(proto[0]) == 2:
            proto = proto[0][1:]
        else:
            proto = proto[0]
        if proto not in self.SUPPORTED_PROTOCOLS:
            self.log.error('Unsupported Protocol: %s' % proto)
        else:
            self.obd_proto = self.SUPPORTED_PROTOCOLS[proto]()
            self.log.debug("Ecu reports %s protocol" % self.obd_proto.desc)
        if self.obd_proto:
            ecu = yield self._call('0100')
            try:
                m = self.obd_proto(ecu)
            except IndexError:
                self.log.debug("Ecu reports wrong protocol, testing all")
            else:
                self.primary_ecu = self._find_primary_ecu(m)
        if self.primary_ecu is None:
            for proto in ['A', '9', '8', '7', '6', '5', '4', '3', '2', '1']:
                proto_test = self.SUPPORTED_PROTOCOLS[proto]()
                setproto = yield self._call('ATTP' + proto)
                if setproto[0] != 'OK':
                    continue
                # self.obd_proto = self.SUPPORTED_PROTOCOLS[proto]()
                test = yield self._call(
                    '0100', commands.PIDS_A,  # @UndefinedVariable
                    test=proto_test)
                if test is not None:
                    self.obd_proto = proto_test
                    self.primary_ecu = self.obd_proto.PRIMARY_ECU
                    break
        if self.primary_ecu is not None:
            self.log.debug(
                "Protocol found: %s %s" %
                (proto, self.obd_proto.desc))
            self.set_commands()
        else:
            self.managed = False

    def connect(self, f):
        f.proto = self

    def set_commands(self):
        getters = commands.pid_getters()

        def filter_result(res, params):
            for i, l in enumerate(res):
                self.log.debug("result for mode %s pid %s:"
                               % (params[i].mode, params[i].pid))
                self.log.debug("    %s" % l[1])
                if l[1] == 'No Result':
                    continue
                for j, b in enumerate(l[1]):
                    if b == '1':
                        m = params[i].get_mode_int()
                        p = params[i].get_pid_int() + j + 1
                        if commands.has_pid(m, p):
                            com = commands[m][p]
                            com.supported = True
                            if com not in getters:
                                self.supported_commands.update(
                                    {com.mode + com.pid: com})
            self.obdconnected = True
#             self.log.debug("Supported commands:")
#             for comm in self.supported_commands.itervalues():
#                 self.log.debug("    %s" % comm)

        l = []
        p = []
        for c in getters:
            l.append(self._call(c.mode + c.pid, c))
            p.append(c)
        d = defer.DeferredList(l)
        d.addCallback(filter_result, p)

    def call(self, command_name):
        if hasattr(commands, command_name):
            command = getattr(commands, command_name)
        else:
            return defer.succeed("Unknown Command")
        if not self.obdconnected:
            if not self.managed:
                return defer.succeed("ECU not recognized")
            return task.deferLater(reactor, 1, self.call, command_name)
        if command.mode + command.pid not in self.supported_commands:
            return defer.succeed("Unsupported Command")
        return self._call(command.mode + command.pid, command)

    def _call(self, command=None, decoder=None, force=False, test=False):
        polled = False
        d = defer.Deferred()
        if self.ready or force:
            if len(self.commands) > 0:
                if command:
                    self.commands.append((command, decoder))
                else:
                    polled = True
                command, decoder = self.commands.pop(0)
            if command:
                self.log.debug("Calling: %s" % command)
                self.ready = False
                self.send(command + '\r')
        else:
            if command:
                self.commands.append((command, decoder,))
            if len(self.commands) > 0:
                reactor.callLater(.1, self._call)  # @UndefinedVariable
                if not command:
                    return
        if not polled:
            self.wait.append((d, decoder, test))
            return d

    def decode(self, lines, decoder, test=False):
        if test:
            try:
                messages = test(lines)
            except:
                return None
        else:
            messages = self.obd_proto(lines)
        r = ''
        for message in messages:
            _data = ''
            #  if message.tx_id == self.primary_ecu:
            try:
                for b in message.data_bytes:
                    h = hex(b)[2:].upper()
                    h = "0" + h if len(h) < 2 else h
                    _data += h
                _data = constrainHex(_data, decoder.bytes, test)
            except ValueError:
                if test:
                    return None
                r += 'No Result\n'
            res, unit = decoder.decode(_data)
            if unit is None:
                unit = ''
            r += ' '.join((str(res), unit))
        if len(r) > 0:
            return r
        if test:
            return None
        return 'No Result'  # no suitable response was returned

    def rawDataReceived(self, data):
        #  self.log.debug(data)
        for byte in data:
            if self.buffer:
                if byte == b'>':
                    if len(self.wait) > 0:
                        d, decoder, test = self.wait.pop(0)
                        if test and decoder is not None:
                            d.callback(
                                self.decode(
                                    self.buffer.parse(), decoder, test))
                        elif self.primary_ecu is not None and\
                                decoder is not None:
                            d.callback(
                                self.decode(
                                    self.buffer.parse(), decoder))
                        else:
                            d.callback(self.buffer.parse())
                    else:
                        r = self.buffer.parse()
                        for c in self.callbacks:
                            c(r)
                    self.buffer = None
                    self.ready = True
                    break
#                 if byte == b'\x07':
#                     self.log.debug('gg')
                if byte == b'\x00':
                    continue
                self.buffer.fill(byte)
            else:
                self.buffer = Frame(byte)


class Frame(object):

    def __init__(self, data=b''):
        self.raw = data
        self.data = []

    def fill(self, byte):
        self.raw += byte

    def parse(self):
        txt = self.raw.decode()
        self.data = [s.strip() for s in re.split("[\r\n]", txt) if bool(s)]
        #  print(self.data)
        return self.data


if __name__ == '__main__':
    import sys
    from twisted.internet.serialport import SerialPort
    from twisted.logger import globalLogBeginner, textFileLogObserver

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)
    log = Logger()

    def show(res, desc):
        log.info("%s: %s" % (desc, res))

    proto = BaseProtocol()

    def test():
        d = proto.call('RPM')  # @UndefinedVariable
        d.addCallback(show, "Régime moteur")
        dd = proto.call('FUEL_LEVEL')  # @UndefinedVariable
        dd.addCallback(show, "Niveau de Carburant")
        ddd = proto.call('DISTANCE_W_MIL')  # @UndefinedVariable
        ddd.addCallback(show, "Kilométrage")
    f = SerialPort(proto, '/dev/pts/3', reactor)
#     reactor.callLater(10,  # @UndefinedVariable
#                       log.debug, proto.checked.__repr__())
    reactor.callWhenRunning(test)  # @UndefinedVariable
    reactor.callLater(30, reactor.stop)  # @UndefinedVariable
#     reactor.callLater(28, stop_monitor)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
