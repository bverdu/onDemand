'''
Created on 22 oct. 2015

@author: babe
'''

import re
from twisted.internet.defer import Deferred
from twisted.logger import Logger

class Modem(object):
    '''
    classdocs
    '''

    def __init__(self, protocol, event_fct=None):
        '''
        Constructor
        '''
        self.log = Logger()
        self.first = True
        self.event = event_fct
        self.callback = None
        self.wait = False
        self.response = ''
        self.protocol = protocol
        self.protocol.addCallback(self.receive)
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
            self.callback = Deferred
            if callback_fct:
                self.callback.addCallback(callback_fct)
            self.wait = True
            self.protocol.write(message + b'\x1a')
        def text_mode(res):
            self.callback = Deferred
            self.callback.addCallback(recipient_set)
            self.wait = True
            self.protocol.write(b'AT+CMGS="' + recipient.encode() + b'"\r')
        def modem_init(res):
            self.first = False
            self.callback = Deferred
            self.callback.addCallback(text_mode)
            self.wait = True
            self.protocol.write(b'AT+CMGF=1\r')
        if self.first:
            self.wait = True
            self.callback = Deferred()
            self.callback.addCallback(modem_init)
            self.protocol.write(b'ATZ\r')
        else:
            modem_init('OK')
        
                