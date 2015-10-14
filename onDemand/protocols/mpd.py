# encoding: utf-8
'''
Created on 30 août 2015

@author: Bertrand Verdu
'''
from twisted.internet import defer
from twisted.logger import Logger
from twisted.protocols.basic import LineReceiver


class MpdProtocol(LineReceiver):
    '''
    Twisted protocol to control remote mpd server
    '''

    def __init__(self):
        '''
        doc
        '''
        self.log = Logger()
        self.delimiter = "\n"
        self.deferreds = []
        self.buff = {}
        self.idle = False
        self.list_index = 0

    def connectionLost(self, reason):
        self.log.error('connection lost : {reason}', reason=reason)
        self._event({'changed': 'disconnected'})
        self.idle = False
        try:
            d = self.deferreds.pop(0)
        except:
            pass
        else:
            d.errback(reason)

    def connectionMade(self):
        self.log.debug('connected')

    def addCallback(self, d):
        self.deferreds.append(d)

    def noidle(self):
        d = defer.Deferred()
        d.addCallback(lambda ignored: ignored)
        self.deferreds.insert(0, d)
        self.sendLine('noidle')
        self.idle = False
#         print('noidle')

    def set_idle(self):
        self.sendLine('idle')
        self.idle = True
#         print('idle')

    def lineReceived(self, line):
        #  print(line)
        if line.startswith('OK MPD'):
            self._event({'changed': 'connected'})
        elif line.startswith('OK'):
            #             print('deferred length: %d' % len(self.deferreds))
            self.list_index = 1
            try:
                d = self.deferreds.pop(0)
            except:
                self.set_idle()
                self._event(self.buff)
                self.buff = {}
                return
            else:
                d.callback(self.buff)
            self.buff = {}
        elif line.startswith('ACK'):
            #             print('deferred length: %d' % len(self.deferreds))
            try:
                d = self.deferreds.pop(0)
            except:
                self.set_idle()
                self._event({'Error': line.split('}')[1]})
                self.buff = {}
                return
            else:
                d.errback(Exception(line.split('}')[1]))
            self.buff = {}
        else:
            if len(line) > 0:
                k = line.split(':')[0]
                if isinstance(self.buff, list):
                    if k in self.buff[self.list_index]:
                        self.list_index += 1
                        self.buff.append({})
                    self.buff[self.list_index].update(
                        {k: ' '.join(line.split()[1:])})
                else:
                    if k in self.buff:
                        self.buff = [self.buff]
                        self.list_index = 1
                        self.buff.append({k: ' '.join(line.split()[1:])})
#                         if str(self.list_index) + k in self.buff:
#                             self.list_index += 1
#                         self.buff.update(
#                             {str(self.list_index) + line.split(':')[0]:
#                              ' '.join(line.split()[1:])})
                    else:
                        self.buff.update(
                            {k: ' '.join(line.split()[1:])})
            return
        if len(self.deferreds) == 0:
            self.set_idle()
