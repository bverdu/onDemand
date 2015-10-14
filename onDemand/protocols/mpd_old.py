'''
Created on 7 janv. 2015

@author: Bertrand Verdu
'''
from twisted.python import log
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import defer, reactor


class MpdEdp():
    pass


class MpdProtocol(LineReceiver):

    def __init__(self):
        '''
        doc
        '''
        self.delimiter = "\n"
        self.deferreds = []
        self.buff = {}
        self.idle = False
        self.list_index = 0

    def connectionLost(self, reason):
        log.err('connection lost : %s' % reason)
        self._event({'changed': 'disconnected'})
        self.idle = False
        try:
            d = self.deferreds.pop(0)
        except:
            pass
        else:
            d.errback(reason)

    def connectionMade(self):
        log.msg('connected')

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
#         print(line)
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


class MpdFactory(ReconnectingClientFactory):

    mimetypes = ['audio/aac', 'audio/mp4', 'audio/mpeg', 'audio/mpegurl',
                 'audio/vnd.rn-realaudio', 'audio/vorbis', 'audio/x-flac',
                 'audio/x-mp3', 'audio/x-mpegurl', 'audio/x-ms-wma',
                 'audio/x-musepack', 'audio/x-oggflac', 'audio/x-pn-realaudio',
                 'audio/x-scpls', 'audio/x-speex', 'audio/x-vorbis',
                 'audio/x-wav', 'application/x-ogm-audio',
                 'audio/x-vorbis+ogg', 'audio/ogg']

    def __init__(self, evtfunc):

        self.connected = False
        self.proto = MpdProtocol()
        self._event = evtfunc
        self.proto._event = self.dispatch_event
        self.status = {'state': 'stop'}
        self.playlist = []
        self.plsversion = '0'
        self.waiting = False
        self.calls = []

    def buildProtocol(self, addr):
        return self.proto

    def watchdog(self):
        d = self.call('status')
        d.addCallback(self.update_status)

    def update_status(self, newst):
        if newst is not None:
            self.status.update(newst)
#             log.msg('status updated: %s' % self.status)
#             self.proto.call('idle', self.dispatch_event, 0)
            reactor.callLater(60,  # @UndefinedVariable
                              self.watchdog)
#         print(self.status)

    def update_playlist(self, playlist):
#         log.err('update playlist: %s %s %s' % (self.status['playlistlength'], len(self.playlist), len(playlist)))
#         dic = {}
        if playlist is not None :
            if not isinstance(playlist, list):
                playlist = [playlist]
            if int(self.status['playlistlength']) == 0:
                self.playlist = []
            else:
                delta = int(self.status['playlistlength']) - len(self.playlist)
#                 print('delta= %d' % delta)
                if delta >= 0:
                    for track in playlist:
                        try:
                            if int(track['Pos']) >= len(self.playlist):
                                self.playlist.append(int(track['Id']))
                            else:
                                self.playlist[int(track['Pos'])] = int(track['Id'])
                        except:
                            continue
                else:
                    for track in playlist:
                        if 'Id' not in track:
                            continue
                        if track == {}:
                            self.playlist.pop()
                            delta += 1
                            continue
                        if delta < 0:
                            self.playlist.pop(int(track['Pos']))
                            delta += 1
                        else:
                            self.playlist[int(track['Pos'])] = int(track['Id'])

#                 if delta > 0:
#                     if len(playlist) == delta:
#                         for i, d in enumerate(playlist):
#                             self.playlist.append(d)
#     #                         dic.update({'playlist': 'appended' + str(i+1)})
#                     else:
#                         for i, d in enumerate(playlist):
#                             if int(d['Pos']) >= len(self.playlist):
#                                 self.playlist.append(d)
#                             else:
#                                 self.playlist[int(d['Pos'])].update(d)
#                 elif delta == 0 and len(playlist) > 0:
#                     for i, d in enumerate(playlist):
#                         self.playlist[int(d['Pos'])].update(d)
#                 else:
#     #                 print(playlist)
#                     for i, d in enumerate(playlist):
#                         if d == {}:
#                             self.playlist.pop()
#     #                         dic.update(
#                                     {'playlist':
#                                          'removed ' +
#                                          str(i+1) + ' Last...'})
#                             delta += 1
#                             continue
#                         if delta < 0:
#     #                         print("popping: %s" % d['Pos'])
#     #                         print(len(self.playlist))
#                             self.playlist.pop(int(d['Pos']))
#     #                         dic.update({'playlist': 'removed ' + str(i+1)})
#                             delta += 1
#                         else:
#                             self.playlist[int(d['Pos'])].update(d)
# #                         dic.update({'playlist': 'modified '+str(i+1)})
#         self.plsversion = str(self.status['playlist'])
#         print(self.plsversion)
#         return dic

#         print(len(self.playlist))
        return {'playlistdata': self.playlist}

    def dispatch_event(self, events, ignored=None):

        def set_connected():
            self.connected = True
            self.call()
            d = self.call('plchanges', self.plsversion)
            d.addCallback(self.update_playlist)
            d.addCallback(self._event)
        d = None
        for evt in events:
            if evt == 'Error':
                log.err(events[evt])
                return
            elif evt == 'changed':
                chg = events[evt]
            else:
                #                 log.msg(events[evt])
                return
            if chg == 'disconnected':
                self.connected = False
                continue
            d = self.call('status')
            if chg == 'connected':
                reactor.callLater(0.2, set_connected)  # @UndefinedVariable
                d.addCallback(self.filter_event)
                d.addCallback(self._event)
            elif chg == 'mixer':
                d.addCallback(self.filter_event,
                              'volume')
                d.addCallback(self._event)
            elif chg == 'player':
                d.addCallback(self.filter_event)
                d.addCallback(self._event)
            elif chg == 'playlist':
#                 print(self.plsversion)
                d.addCallback(self.filter_event,
                              'playlist')
                d.addCallback(self._event)
            return d

    def filter_event(self, data, filtr=None):
        if data is None:
            return {}
        if not isinstance(data, list):
            data = [data]
        if filtr is not None:
            for d in data:
                for d in data:
                    self.status.update(d)
            if filtr == 'playlist':
                d = self.call('plchanges', self.plsversion)
                d.addCallback(self.update_playlist)
                return d
            else:
                for d in data:
                    self.status.update(d)
                return {filtr: self.status[filtr]}
        else:
            dic = {}
            for d in data:
                for it in d.items():
                    if it not in self.status.items():
                        self.status.update(dict([it]))
                        dic.update(dict([it]))
            return dic
        return {}

    def call(self, command=None, params=None):
        d = defer.Deferred()
        if command is not None:
            self.proto.addCallback(d)
        if not self.connected:
            self.calls.append((command, params))
        else:
            if len(self.calls) > 0:
                command, params = self.calls.pop(0)
            if command is None:
                del d
                return
            else:
                if params is not None:
                    c = ' '.join([command, params])
                else:
                    c = command
                if self.proto.idle:
                    self.proto.noidle()
                self.proto.sendLine(c)
            if len(self.calls) > 0:
                self.call()
        return d

def mpdclient(addr, port):
    f = MpdFactory()
    reactor.connectTCP(addr, port, f)  # @UndefinedVariable
    return f

if __name__ == '__main__':
    from twisted.internet.task import deferLater

    def print_fct(result):
        print('func result: %s' % result)
        if isinstance(result, list):
            print(len(result))
            for r in result:
                if not 'Id' in r:
                    print('!!!!!!!!!!!!! %s !!!!!!!!!!!' % r)
                print(r)
#                 print(r)
        else:
            print('single result: %s' % result)

    def print_event(evt=''):
        print('intercepted: %s' % evt)
    mpd = MpdFactory(print_event)
    reactor.connectTCP("192.168.0.9", 6600, mpd)  # @UndefinedVariable
    print('ready')

    def test():
        if mpd.connected:
#             for i in xrange(5):
#                 d = deferLater(reactor,
#                                i,
#                                mpd.call,
#                                *('pause', str(int(i % 2))))
#                 d.addCallback(print_fct)
#             d = mpd.call('stop')
#             d.addCallback(print_fct)
            d = mpd.call('status')
            d.addCallback(print_fct)
#             d = mpd.call('stop')
#             d.addCallback(print_fct)
#             d = mpd.call('playid', '25')
#             d.addBoth(print_fct)
            d = mpd.call('plchanges', '0')
            d.addCallback(print_fct)
#             d = mpd.call('playlistinfo')
#             d.addCallback(print_fct)
#             d = mpd.call('addid http://192.168.0.10:8200/MediaItems/2108.flac')
#             d.addCallback(print_fct)
#             d = mpd.call('sticker', 'set song "http://192.168.0.10:8200/MediaItems/2108.flac" toto tata')
#             d.addCallback(print_fct)
#             d = mpd.call('sticker', 'list song "http://192.168.0.10:8200/MediaItems/2108.flac"')
#             d.addCallback(print_fct)
            d = mpd.call('playlistid', '184')
            d.addCallback(print_fct)
#             d = mpd.call('playlistid')
#             d.addCallback(print_fct)
#             d = mpd.call('playlistinfo', '227' )
#             d.addCallback(print_fct)
        else:
            reactor.callLater(1, test)  # @UndefinedVariable
    reactor.callWhenRunning(test)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
