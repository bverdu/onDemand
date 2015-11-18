# encoding: utf-8

import uuid
import re
from twisted.internet import reactor, defer
from twisted.internet.protocol import ClientFactory
from twisted.logger import Logger
from onDemand.protocols.serial import serialProtocol, serialEndPoint
from onDemand.plugins import Client



class SmsFactory(ClientFactory, Client):
    room = 'NA'
    actions = ('sendsms, readsms')
    
    def __init__(self, event_fct=None):
        self.protocol = serialProtocol()
        self.uid = uuid.uuid4()
        self.protocol.factory = self
        self.log = Logger()
        self.first = True
        self.event = event_fct
        self.callback = None
        self.wait = False
        self.response = ''
        self.resp_re = re.compile(
                    r'^OK|ERROR|(\+CM[ES] ERROR: \d+)|(COMMAND NOT SUPPORT)$')
        
    def receive(self, line):
        if self.wait:
            if self.resp_re.match(line):
                self.wait = False
                self.response.append(line)
                if line.startswith('ERROR'):
                    self.log.critical('error from Modem: %s' % line)
                    if self.callback:
                        self.callback.errback(self.response)
                else:
                    if self.callback:
                        self.callback.callback(self.response)
                self.response = ''
                if self.callback:
                    self.callback = None
            else:
                self.response.append(line)
        elif self.event:
            self.event(line)   
        else:
            self.log.debug('unmanaged message from Modem: %s' % line)
            
    def sendsms(self, recipient, message, callback_fct=None):
        def recipient_set(res):
            self.log.debug(
                'do we have > ? ==> %s' % ('OK' if res == '>' else 'No: ' + res))
            self.callback = defer.Deferred
            if callback_fct:
                self.callback.addCallback(callback_fct)
            self.wait = True
            self.protocol.send(message + b'\x1a')
        def text_mode(res):
            self.callback = defer.Deferred
            self.callback.addCallback(recipient_set)
            self.wait = True
            self.protocol.send(b'AT+CMGS="' + recipient.encode() + b'"\r')
        def modem_init(res):
            self.first = False
            self.callback = defer.Deferred
            self.callback.addCallback(text_mode)
            self.wait = True
            self.protocol.send(b'AT+CMGF=1\r')
        if self.first:
            self.wait = True
            self.callback = defer.Deferred()
            self.callback.addCallback(modem_init)
            self.protocol.send(b'ATZ\r')
        else:
            modem_init('OK')
            
    def _write(self, txt):
        self.protocol.send(txt.encode())
        
def get_sms(deviceName, **kwargs):
    if 'event_fct' in kwargs:
        f = SmsFactory(event_fct=kwargs['event_fct'])
        del kwargs['event_fct']
    else:
        f = SmsFactory()
    e = serialEndPoint(f.protocol, deviceName, reactor, **kwargs)
    e.connect(f.uid, f.receive)
    return e, f
    
if __name__ == '__main__':
    def show(line):
        print('test result: %s' % line)
#         reactor.stop()
        
    def test(fact):
        fact._write('help\r\n')
        
    edp, fact = get_sms('/dev/ttyACM0', event_fct=show, baudrate=38400, rtscts=1)
    reactor.callWhenRunning(test, fact)  # @UndefinedVariable
    reactor.callLater(10, reactor.stop)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
    
    