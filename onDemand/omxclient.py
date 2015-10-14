# encoding: utf-8
'''
Created on 4 févr. 2015

@author: Bertrand Verdu
'''
import os
import math
from twisted.application.service import Service
from twisted.internet import task, protocol, defer, utils
from twisted.python import log

from protocols.dbus import DbusConnection,\
    ODbusProxy, get_user_sessions
# from twisted.internet import gireactor
# gireactor.install()
from twisted.internet import reactor
from upnpy.utils import didl_decode, id_array
from onDemand.utils import mpris_decode,\
    mpristime_to_upnptime, upnptime_to_mpristime, Timer
import xml.etree.cElementTree as et


class Omxclient(Service):
    bus = None
    addrs = None
    token = 0
    con = None
    _state = 'Pending'
    _volume = 1
    max_volume = 100
    seconds = 0
    uri = ''
    properties = None
    player = None
    is_connected = False
    pending = True
    event_msg = {
        'Paused': ['PAUSED_PLAYBACK', 'Paused'],
        'Playing': ['PLAYING', 'Playing'],
        'Pending': ['TRANSITIONNING', 'Buffering'],
        'Stopped': ['STOPPED', 'Stopped']}
    _metadata = {}
    metadata_str = ''
    metadata = {}
    songid = 0
    maxsongid = 0
    _duration = 0
    upnp_duration = '0:00:00'
    reltime = '0:00:00.000'
    _playlist = []
    playlist = []
    _track_URI = ''
    idArray = ''
    repeat = False
    shuffle = False
    tracksmax = 1000
    mtlist = ''
    timer = None
    _next = False

    def __init__(self, program='', args=None, **kwargs):
        if args:
            self.process_args = [program] + [arg for arg in args.split()]
        else:
            self.process_args = [program]
        self.process_path = program
        self.process = PlayerProcess(self)
        self.playername = program.split("/")[-1]

    def startService(self):
        self.con = DbusConnection()
        d = self.con.connect()
        d.addCallbacks(self.connected, self.not_connected)

    def connected(self, bus):
        log.msg('connected: %s' % bus)
        self.bus = bus

        def got_properties(proxy):
            d = self.player.get_proxy()
            d.addCallback(got_player)
            return d

        def got_player(proxy):
            self.con.watch_process(
                'org.mpris.MediaPlayer2.omxplayer', self.connection_lost)
            self.pending = False
            reactor.callLater(6,  # @UndefinedVariable
                              lambda: setattr(self, 'polling', True))
            reactor.callLater(  # @UndefinedVariable
                7, self.poll_status)

        if not self.properties:
            self.properties = ODbusProxy(
                self.bus,
                bus_name='org.mpris.MediaPlayer2.omxplayer',
                object_path='/org/mpris/MediaPlayer2',
                interface='org.freedesktop.DBus.Properties',
                timeout=5)
            self.player = ODbusProxy(
                self.bus,
                bus_name='org.mpris.MediaPlayer2.omxplayer',
                object_path='/org/mpris/MediaPlayer2',
                interface='org.mpris.MediaPlayer2.Player',
                timeout=5)
            d = self.properties.get_proxy()
        else:
            return defer.succeed(None)
        d.addCallback(got_properties)
        return d

    def connection_lost(self, *args, **kwargs):
        log.err('connection lost')
        #for arg in args:
            #log.err(arg)
        if 'really_lost' in kwargs:
            really_lost = kwargs['really_lost']
        else:
            really_lost = False
        if really_lost:
            self.is_connected = False
        else:
            self.is_connected = not self.is_connected
        if not self.is_connected:
            if self.process.launched:
                log.err('launched')
                self.connect()
            else:
                log.err('not launched')
                self.properties = None
                self.player = None
                self.polling = False
                self.changed_state({'PlaybackStatus': 'Stopped'})
                self.timer = None
                self.seconds = 0
                self.reltime = '0:00:00.000'
            #self.changed_state({'PlaybackStatus': 'Stopped'})

    def not_connected(self, err):
        self.bus = None
        log.err('Dbus Connection failed: %s' % err)

    def connect(self, err=None):
        log.msg('connect')
        if not self.bus:
            if not self.addrs:
                self.addrs = get_user_sessions()
                log.msg(self.addrs)
                if len(self.addrs) > 0:
                    if self.con:
                        d = self.con.connect_addr(self.addrs.pop(0))
                        d.addCallbacks(self.connected, self.connect)
                    else:
                        d = task.deferLater(reactor, 2, self.connect)
                else:
                    self.addrs = None
                    d = task.deferLater(reactor, 2, self.connect)
            return d
        else:
            return self.connected(self.bus)

    def poll_status(self):
        if self.polling:
            if not self.pending:
                if self.process.launched:
                    self.pending = True
                    d = self.properties.Position()
                    d.addCallbacks(self.update_position, self.call_failed)
                    d.addCallback(
                        lambda ignored: setattr(self, 'pending', False))
            reactor.callLater(5, self.poll_status)  # @UndefinedVariable

    def call_failed(self, err):
        self.pending = False
        log.msg(err)

    def got_event(self, *args, **kwargs):
        if args[0] == 'properties':
            if args[1][0] == 'org.mpris.MediaPlayer2.Player':
                self.changed_state(args[1][1])
            elif args[1][0] == 'org.mpris.MediaPlayer2.TrackList':
                self.changed_tracks()
        elif args[0] == 'tracklist':
            self.changed_tracks()

    def update_position(self, pos):
        if self._state in ('Paused', 'Stopped'):
            log.msg('del timer')
            self.seconds = int(pos)/1000000
            self.timer = None
        elif self.timer:
            log.msg('timer alive')
            self.timer.set(int(pos)/1000000)
        else:
            self.seconds = int(pos)/1000000

    def changed_state(self, *args, **kwargs):
        for arg in args:
            if isinstance(arg, dict):
                if 'PlaybackStatus' in arg:
                    log.err(arg)
                    if self._state != arg['PlaybackStatus']:
                        self._state = arg['PlaybackStatus']
                        self.upnp_eventAV(
                            self.event_msg[self._state][0], 'TransportState')
                        self.oh_eventPLAYLIST(
                            self.event_msg[self._state][1], 'transportstate')
                if 'Volume' in arg:
                    if self._volume != arg['Volume']:
                        self._volume = arg['Volume']
                        self.upnp_eventRCS(int(self._volume*100), 'Volume')
                        self.oh_eventVOLUME(int(self._volume*100), 'volume')
                if 'Metadata' in arg:
                    self.update_metadata(arg['Metadata'])

    def update_metadata(self, metadata):
        songid = None
        if isinstance(metadata, dict):
            if self._metadata == metadata:
                return
            else:
                self._metadata = metadata
                self.metadata = mpris_decode(metadata)
        elif isinstance(metadata, str):
            if self.metadata_str == metadata:
                return
            else:
                self.metadata_str = metadata
                self.metadata = didl_decode(metadata)
                log.msg(self.metadata)
        else:
            log.err('Bad metadata format : %s' % metadata)
            return
        if 'songid' in self.metadata:
                if self.songid != int(self.metadata['songid']):
                    songid = int(self.metadata['songid'])
        if songid:
            self.songid = songid
            self.upnp_eventAV(int(self.songid), 'CurrentTrack')
            self.oh_eventPLAYLIST(int(self.songid), 'id')
            self.oh_eventTIME(1, 'trackcount')
        if 'duration' in self.metadata:
            if self._duration != self.metadata['duration']:
                duration = int(self.metadata['duration'])
                log.msg('duration: %d' % duration)
                if duration < 1:
                    self.upnp_duration = "0:00:00"
                    self._duration = 0
                else:
                    self._duration = duration
                    self.upnp_duration = mpristime_to_upnptime(duration)
                log.msg('track length: %s'
                        % self.upnp_duration, loglevel=logging.DEBUG)
                self.upnp_eventAV(self.upnp_duration,
                                  'CurrentTrackDuration')
                self.oh_eventINFO(int(self._duration//1000000), 'duration')
                self.oh_eventTIME(int(self._duration//1000000), 'duration')
        if 'url' in self.metadata:
            if self._track_URI != self.metadata['url']:
                self._track_URI = self.metadata['url']
                self.upnp_eventAV(self._track_URI, 'AVTransportURI')
                self.oh_eventINFO(self._track_URI, 'uri')
                self.upnp_eventAV(self._track_URI, 'CurrentTrackURI')
        if 'mpris:artUrl' in self.metadata:
            url = self.parent.register_art_url(self.metadata['mpris:artUrl'])
            self.metadata['albumArtURI'] = url
        self.oh_eventINFO(self.metadata_str, 'metadata')
        self.upnp_eventAV(self.metadata_str, 'AVTransportURIMetaData')

    def changed_tracks(self):
        self.oh_eventPLAYLIST(id_array(self.playlist), 'idarray')

    def upnp_eventAV(self, evt, var):
        pass

    def upnp_eventCM(self, evt, var):
        pass

    def upnp_eventRCS(self, evt, var):
        pass

    def oh_eventPLAYLIST(self, evt, var):
        pass

    def oh_eventINFO(self, evt, var):
        pass

    def oh_eventTIME(self, evt, var):
        pass

    def oh_eventVOLUME(self, evt, var):
        pass

    def get_track_id(self):
        return self.songid

    def get_track(self, track):
        ind = self.playlist.index(int(track))
        return defer.succeed((self._playlist[ind][1], self._playlist[ind][2],))

    def get_tracks(self, tracks):
        tr = []
        for track in tracks:
            ind = self.playlist.index(int(track))
            tr.append(
                (self._playlist[ind][0],
                 self._playlist[ind][1],
                 self._playlist[ind][2],))
        tracks = tr
        if not isinstance(tracks, list):
                tracks = [tracks]
        tl = et.Element('TrackList')
        for track in tracks:
            #             log.err('track: %s' % track[0])
            en = et.Element('Entry')
            i = et.Element('Id')
            i.text = str(track[0])
            en.append(i)
            uri = et.Element('Uri')
            uri.text = track[1].decode('utf-8')
            en.append(uri)
            md = et.Element('Metadata')
            md.text = track[2]
            en.append(md)
            tl.append(en)
        return defer.succeed(et.tostring(tl))

    def get_state(self):
        return self._state

    def get_rate(self):

        return self.rate

    def get_track_duration(self):
        try:
            duration = self._track_duration
        except:
            duration = '00:00:00'
        return duration

    def get_track_URI(self):
        try:
            uri = self._track_URI
        except:
            uri = ''
        return uri

    def get_track_md(self):
        return self.metadata_str

    def get_relcount(self):
        return 2147483647

    def get_abscount(self):
        return 2147483647

    def get_abstime(self):
            return '00:00:00'

    def get_reltime(self, fmt='UPNP'):
        if self.timer is not None:
            s = self.timer.get()
            if (self._duration//1000000 - s) < 2:
                if not self._next:
                    log.msg('next!!')
                    self._next = True
                    reactor.callLater(3, self.next)  # @UndefinedVariable
            if fmt == 'UPNP':
                t = mpristime_to_upnptime(s)
            elif fmt == 'seconds':
                t = int(s)
            else:
                # msec
                t = s
        else:
            if fmt == 'UPNP':
                t = self.reltime
            else:
                t = self.seconds
        return t

    def get_volume(self):
        if self.process.launched:
            def noVolume(err):
                if self._muted:
                    return 0
                else:
                    return self._volume

            def convert_volume(vol):
                self._volume = int(float(vol))
                log.msg("volume= %d" % self._volume, loglevel=logging.DEBUG)
                return self._volume

            d = self.properties.Volume()
            d.addCallbacks(convert_volume, noVolume)
            return d
        else:
            return 1

    def set_volume(self, channel, volume):
        if self.process.launched:
            if int(volume) != 0:
                d = self.properties.Volume(float(int(volume)/100.00))
            else:
                if self._muted:
                    d = self.properties.Volume(float(self._volume))
                else:
                    d = self.properties.Volume(0.00)
            d.addErrback(self.call_failed)
            reactor.callLater(0.1, self.changed_state,  # @UndefinedVariable
                              {'Volume': float(int(volume)/100.00)})

    def set_track_URI(self, uri, md=''):
        log.msg("set track uri : %s " % uri, loglevel=logging.DEBUG)
        try:
            log.msg("current uri : %s " % self._track_URI, loglevel=logging.DEBUG)
        except:
            pass
        if uri != self._track_URI:
            self.changed_state({'Metadata': md.encode('utf-8')})

    def set_position(self, newpos, fmt='UPNP'):
        if self.process.launched:
            def transition(obj):
                current_state = self._state
                self.changed_state({'PlaybackStatus': 'Pending'})
                reactor.callLater(  # @UndefinedVariable
                    0.5,
                    self.changed_state,
                    {'PlaybackStatus': current_state})
            if fmt == 'UPNP':
                newtime = upnptime_to_mpristime(newpos)
                offset = newtime - self.seconds
            else:
                offset = float(newpos) - self.seconds
            d = self.player.Seek(offset)
            d.addCallbacks(transition, self.call_failed)
            return d

    def set_repeat(self, repeat):
        log.err('repeat=%s' % repeat)
        self.repeat = repeat
        self.oh_eventPLAYLIST(self.repeat, 'repeat')

    def set_shuffle(self, shuffle):
        self.shuffle = shuffle

    def play(self, songid=None):
        log.err('play :%s' % songid)

        def playing(ignored, trackid=None, md=None):
            log.err('playing')
            self.pending = False
            if not self.timer:
                log.msg('create timer')
                self.timer = Timer()
                self.timer.set(self.seconds)
            else:
                log.msg('resume timer')
                self.timer.resume()
            if trackid:
                self.changed_state(
                    {'PlaybackStatus': 'Playing',
                     'Metadata': {'songid': trackid}}, {'Metadata': md})
            else:
                self.changed_state({'PlaybackStatus': 'Playing'})
        log.msg('from %s to %s' % (self._state, 'Play'))
        if songid:
            songid = int(songid)
            if self.process.launched:
                log.err('killing player')
                self.player.Stop()
                task.deferLater(reactor, 1, self.play, songid)
            else:
                volmb = 2000.0 * math.log10(self._volume)
                self.pending = True
                args = self.process_args\
                    + ['--vol']\
                    + [str(volmb)]\
                    + [self._playlist[self.playlist.index(songid)][1]]
#                 args = self.process_args +\
#                     [self._playlist[self.playlist.index(songid)][1]]
                reactor.spawnProcess(  # @UndefinedVariable
                    self.process,
                    self.process_path,
                    tuple(args),
                    env=os.environ)
                log.msg('play in one second')
                reactor.callLater(  # @UndefinedVariable
                    1,
                    playing,
                    *(0,
                      songid,
                      self._playlist[self.playlist.index(songid)][2],))
        else:
            if self.process.launched:
                if self._state == 'Paused':
                    if not self.pending:
                        self.pending = True
                        d = self.player.Pause()
                        d.addCallbacks(playing, self.call_failed)
                    else:
                        reactor.callLater(  # @UndefinedVariable
                            0.2, self.play)
            else:
                volmb = 2000.0 * math.log10(self._volume)
                self.pending = True
                args = self.process_args\
                    + ['--vol']\
                    + [str(volmb)]\
                    + [self.track_URI]
                reactor.spawnProcess(  # @UndefinedVariable
                    self.process,
                    self.process_path,
                    tuple(args),
                    env=os.environ)
                reactor.callLater(  # @UndefinedVariable
                    1,
                    playing,
                    *(0, self.songid, self.metadata_str))

    def pause(self):
        def paused(ignored):
            self.pending = False
            self.timer.stop()
#             self.seconds = self.timer.get()
#             self.timer = None
            self.changed_state({'PlaybackStatus': 'Paused'})
        log.msg('from %s to %s' % (self._state, 'Pause'))
        if self._state != 'Paused':
            if not self.pending:
                self.pending = True
                d = self.player.Pause()
                d.addCallbacks(paused, self.call_failed)
            else:
                reactor.callLater(0.3, self.pause)  # @UndefinedVariable

    def stop(self):
        if self._state != 'Stopped':
            self.timer = None
            self.seconds = 0
            self.player.Stop()
            self.reltime = '00:00:00'
            self.changed_state({'PlaybackStatus': 'Stopped'})

    def next(self):
        if self._next:
            self._next = False
        if len(self.playlist) > 0:
            if self.songid == self.playlist[-1]:
                if self.repeat:
                    self.play(songid=self.playlist[0])
            else:
                self.play(
                    songid=self.playlist[
                        self.playlist.index(self.songid) + 1])

    def previous(self):
        if len(self.playlist) > 0:
            if self.songid == self.playlist[0]:
                if not self.repeat:
                    return
            self.play(
                songid=self.playlist[
                    self.playlist.index(self.songid) - 1])

    def volUp(self):
        if self._volume == 0:
            vol = self.get_volume()
            try:
                newvol = vol + 5
            except:
                newvol = self._volume*100 + 5
            return self.set_volume('Master', newvol)
        else:
            if self._volume > 95:
                return
            newvol = self._volume*100 + 5
            return self.set_volume('Master', newvol)

    def volDown(self):
        if self._volume > 0.05:
            newvol = self._volume*100 - 5
            return self.set_volume('Master', newvol)
        else:
            self._volume = 0
            return self.set_volume('Master', 0)

    def insert(self, url, afterid, metadata, checked=False):
        if 'youtube' in url and not checked:
            # eclipse workaround !!!
            y = os.environ
            y.update({'PYTHONPATH': '/usr/bin/python'})  # / eclipse workaround
            d = utils.getProcessOutput(
                '/usr/bin/youtube-dl',
                ['-g', '-f', 'bestaudio', url],
                env=y,
                reactor=reactor)
            d.addCallback(
                lambda u: self.insert(
                    u.split('\n')[0], afterid, metadata, True))
            return d
#         log.err('playlist length:%s' % len(self._playlist))
        self.maxsongid += 1
        if len(self._playlist) == 0:
            self._playlist.append([self.maxsongid, url, metadata])
        else:
            if afterid == '0':
                self._playlist.insert(0, [self.maxsongid, url, metadata])
            else:
                self._playlist.insert(
                    self.playlist[self.playlist.index(int(afterid))],
                    [self.maxsongid, url, metadata])
#         log.err('real playlist: %s' % self._playlist)
        self.playlist = [i[0] for i in self._playlist]
#         log.err('new playlist: %s' % self.playlist)
#         log.err('metadata dic: %s' % metadata)
        self.oh_playlist = [str(i) for i in self.playlist]
        self.idArray = id_array(self.playlist)
        self.changed_tracks()
        if self.songid == 0:
            self.update_metadata({'songid': 1})
        return defer.succeed(self.maxsongid)

    def delete(self, songid):
        #  log.err(self.playlist)
        try:
            suppressed = self.playlist.index(int(songid))
        except IndexError:
            pass
        else:
            self._playlist.pop(suppressed)
            self.playlist.pop(suppressed)
            self.idArray = id_array(self.playlist)
            self.changed_tracks()

    def clear(self):
        self.playlist = []
        self._playlist = []
        self.songid = 0
        self.idArray = ''
        self.changed_state('TrackList', {}, '')


class PlayerProcess(protocol.ProcessProtocol):
    '''
    Manage player process
    '''
    launched = False

    def __init__(self, parent):
        self.parent = parent
        parent.protocol = self
        self.data = ''

    def connectionMade(self):
        self.transport.closeStdin()
        reactor.callLater(0, self.parent.connect)  # @UndefinedVariable
        self.launched = True
        log.err('process started')

    def processEnded(self, reason):
        log.err('process ended')
        if reason.value.exitCode != 0:
            log.err("processEnded, status %s" % reason.value.exitCode)
        self.launched = False
        self.parent.connection_lost(really_lost=True)

    def shutdown(self):
        self.transport.loseConnection()

if __name__ == '__main__':
    def test():
        pl.StartService()
        reactor.callLater(  # @UndefinedVariable
            5, pl.play, 'http://192.168.0.10:8200/MediaItems/1418.avi')
        # pl.play('http://192.168.0.10:8200/MediaItems/1418.avi')
        reactor.callLater(15,  # @UndefinedVariable
                          pl.pause)
        reactor.callLater(20,  # @UndefinedVariable
                          pl.play)
    print('starting')
    pl = Omxclient('/usr/bin/omxplayer')
    reactor.callWhenRunning(test)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
