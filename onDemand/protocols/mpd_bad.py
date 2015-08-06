# -*- coding: utf-8 -*-
'''
Created on 29 déc. 2014

@author: babe
'''

from twisted.python import log
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import defer, reactor


class MpdProtocol(LineReceiver):
    __slots__ = ['__funcs',
                 'delimiter',
                 '__current',
                 '__term',
                 '__dict__']

    def __init__(self):
        '''
        doc
        '''
        self._func = []
        self.delimiter = "\n"
        self.__current = ""
        self.__term = 0.00
        self._connected = False
        self.idle = False
        self.buff = []
        self.ignore = False
        self.wait = False
        self.pending = []

    def unset_idle(self, ignored):
#         print('noidle: %s' % ignored)
        self.idle = False

    def connectionLost(self, reason):
        log.err('connection lost : %s' % reason)
        self.wait = False
        self._connected = False
        self._event(['changed: disconnected'])

    def connectionMade(self):
#         self._connected = True
        self.wait = False
        log.err('connected')
        self._event(['changed: connected'])
#         self._event('changed: connected')

    def lineReceived(self, line):
#             print(line)
#         print('functions: %s' % self._func)
            if line.startswith('OK MPD'):
                self._connected = True
                self.wait = False
                return
            elif line.startswith('OK'):
                print('!')
                self.wait = False
                if self.idle:
                    self._event(self.buff)
                    self.buff = []
                    return
                try:
                    f, d = self._func.pop(0)
                except:
                    self._event(self.buff)
                else:
                    f(self.buff, d)
                self.buff = []
            elif line.startswith('ACK'):
                print('?')
                self.wait = False
                try:
                    f, d = self._func.pop(0)
                except:
                    self._event(Exception(line.split('}')[1]))
                else:
                    f(Exception(line.split('}')[1]), d)
                self.buff = []
            else:
                print('.')
                self.buff.append(line)
                
                
#         if line.startswith('OK MPD'):
#             self._connected = True
#             if self.idle:
#                 self._event(['changed: connected'])
#                 self.sendLine('idle')
#                 print('idle')
#                 self.idle = True
#                 return
#             else:
#                 if len(self._func) == 0:
#                     self.sendLine('idle')
#                     self.idle = True
#                 return
#         elif line.startswith('OK'):
#             if self.idle:
#                 self._event(self.buff)
#                 self.buff = []
#                 self.sendLine('idle')
#                 print('idle')
#                 self.idle = True
#                 return
#             f,c,d = self._func.pop(0)
#             f(self.buff, d, c)
#             self.buff = []
#             if len(self._func) == 0:
#                 self.sendLine('idle')
#                 print('idle')
#                 self.idle = True
#         elif line.startswith('ACK'):
#             log.err('mpd protocol error : %s' % line)
#             f,c, d = self._func.pop(0)
#             f(Exception(line.split('}')[-1]), d, c)
#             self.buff = []
#             if len(self._func) == 0:
#                 self.sendLine('idle')
#                 print('idle')
#                 self.idle = True
#         else:
#             if len(line) >1:
#                 self.buff.append(line)
#         if line.startswith('OK'):
#             if len(line) > 2:
#                 return
#             if len(self.buff) > 0:
#                 try:
#                     f,d = self._func.pop(0)
#                 except:
#                     self._event(self.buff)
#                 else:
#                     f(self.buff, d)
#             self.buff = ''
#             if self.idle is False:
#                 if self._connected:
#                     self.idle = True
#                     reactor.callLater(0.2,  # @UndefinedVariable
#                                 self.sendLine,
#                                 'idle')
#         elif line.startswith('ACK'):
#             print('err')
#             log.err('mpd protocol error: %s' % line)
#             if self._func is not None:
#                 self._func = None
#                 raise Exception(line.split('}')[-1])
#             self.buff = ''
#             if not self.idle:
#                 if self._connected:
#                     self.idle = True
#                     reactor.callLater(0.2,  # @UndefinedVariable
#                                 self.sendLine,
#                                 'idle')
#         else:
#             if len(line) > 1:
#                 self.buff += line + '\n'

#     def addCallback(self, func, d):
# #         print('func added')
#         self._func.append((func, d))

    def call(self, called=None, func=None, d=None):
        def fake(ignored, nocare):
            pass
        if called is not None:
            self.pending.append(called)
            if called not in ('idle','noidle') :
                self._func.append((func, d))
                print('register callback function %s position : %d' %(called, len(self._func)))
        if self._connected:
            while True:
                if self.wait:
                    print('*')
                    if len(self.pending) > 0:
                        reactor.callLater(0.5, self.call)  # @UndefinedVariable
                    break
                try:
                    cal = self.pending.pop(0)
                except:
                    break
                else:
                    if cal == 'noidle':
                        if self.idle:
                            self._func.insert(0, (fake, 0))
                            self.sendLine('noidle')
                            self.wait = True
                            self.idle = False
                        return
                    elif cal == 'idle':
                        if self.idle:
                            return
                        else:
                            self.idle = True
                    else:
                        self.wait = True
                    self.sendLine(cal)
        else:
            if len(self.pending) > 0:
                reactor.callLater(1, self.call)  # @UndefinedVariable
#         if called is not None:
#             self.pending.append(called)
#         if self._connected:
#             while len(self.pending) > 0:
#                 c = self.pending.pop(0)
#                 print(c)
#                 if self.idle:
#                     print('noidle')
#                     self.sendLine('noidle')
#                     self.idle = False
#                 reactor.callLater(0.2,  # @UndefinedVariable
#                                   self.sendLine,
#                                   c)
#         else:
#             if len(self.pending) > 0:
#                 print('differed call : %s' % self.pending)
#                 reactor.callLater(0.5,  # @UndefinedVariable
#                                   self.call)


class MpdFactory(ReconnectingClientFactory):
    
    ACTIONS = ('playid', 'pause', 'next', 'previous', 'setvol', 'seekid', 'seekcur', 'stop')

    def __init__(self, evtfunc):
        self.proto = MpdProtocol()
        self._event = evtfunc
        self.proto._event = self.dispatch_event
        self.status = {}
        self.stats = {}
        self.connected = False

    def buildProtocol(self, addr):
        return self.proto

    def watchdog(self):
        d = self.call('status')
        d.addCallback(self.update_status)

    def update_status(self, newst):
        if newst is not None:
            self.status.update(newst)
            print('status updated: %s' % self.status)
#             self.proto.call('idle', self.dispatch_event, 0)
            reactor.callLater(60,  # @UndefinedVariable
                            self.watchdog)
#         print(self.status)

    def dispatch_event(self, events, ignored=None):
        d = None
        log.err('eveeeeennntt: %s' % events)
#         for evt in events.split('\n'):
        for evt in events:
            if len(evt.split()) > 1:
                chg = evt.split()[1]
            else:
                continue
            if chg == 'disconnected':
                continue
            if d is None:
                d = self.call('status')
            if chg == 'connected':
                self.connected = True
                d.addCallback(self.update_status)
#                 d.addCallback(self.proto.call,
#                               *('idle',
#                                 self.dispatch_event,
#                                 0))
                return d
            elif chg == 'mixer':
                d.addCallback(self.filter_event,
                              'volume')
                d.addCallback(self._event)
            elif chg == 'player':
                d.addCallback(self.filter_event)
                d.addCallback(self._event)
            return d

    def filter_event(self, data, filtr=None):
        if data is None:
            return {}
        if filtr is not None:
            self.status.update(data)
            return {filtr: self.status[filtr]}
        else:
            dic = {}
            for it in data.items():
                if it not in self.status.items():
                    self.status.update(dict([it]))
                    dic.update(dict([it]))
            return dic

    def call(self, command, params=None):
#         if command not in self.proto.pending:
#             log.err('command %s not in %s' % (command, self.proto.pending))

        def func_return(result, d):
            #             print('func callback: %s' % result)
            dic = {}
            for l in result:
                if len(l) > 1:
                    dic.update({l.split(':')[0]: " ".join(l.split()[1:])})
            print('callback : %s %s' % (result, dic))
            d.callback(dic)
#             i = self.call('idle')
#             i.addCallback(self._event)

        log.msg('Mpdsend:%s' % command, loglevel='info')
        #             print(command)
        if params is None:
            c = command
        else:
            c =' '.join([command, params])
        d = defer.Deferred()
        self.proto.call('noidle')
        reactor.callLater(0.2,  # @UndefinedVariable
                          self.proto.call,
                          *(c, func_return, d))
        reactor.callLater(1,  # @UndefinedVariable
                          self.proto.call,
                          'idle')
        return d
#             if params is None:
#                 lin = command
#             else:
#                 lin = ' '.join([command, params])
#             if command not in self.ACTIONS:
#                 d = defer.Deferred()
# #                 self.proto.addCallback(func_return, d)
#                 self.proto.call(lin, func_return, d)
#                 return d
#             else:
#                 self.proto.call(lin)
#                 return defer.succeed(None)
#         else:
#             return defer.succeed(None)

if __name__ == '__main__':
    from twisted.internet.task import deferLater

    def print_fct(result):
        print('func result: %s' % result)

    def print_event(evt=''):
        print('intercepted: %s' % evt)
    mpd = MpdFactory(print_event)
    reactor.connectTCP("192.168.0.9", 6600, mpd)  # @UndefinedVariable
    print('ready')
#     r = mpd.call('currentsong')
#     r.addCallback(print_fct)
#     d = mpd.call('currentsong')
#     d.addCallback(print_fct)
    for i in xrange(5):
        d = deferLater(reactor,
                       i,
                       mpd.call,
                       *('pause', str(int(i%2))))
        d.addCallback(print_fct)
    d = mpd.call('stop')
    d.addCallback(print_fct)
    d = mpd.call('stop')
    d.addCallback(print_fct)
    d = mpd.call('playid', '544')
    d.addCallback(print_fct)
    
        
    
    reactor.run()  # @UndefinedVariable
