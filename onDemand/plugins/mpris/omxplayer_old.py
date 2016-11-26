# encoding: utf-8
'''
Created on 29 oct. 2016

@author: Bertrand Verdu
'''
import os
import psutil
import math
from collections import OrderedDict
from twisted.python.failure import DefaultException
from twisted.application.service import Service
from twisted.logger import Logger
from upnpy_spyne.utils import didl_decode, dict2xml
from onDemand.protocols.dbus import ODbusProxy, get_user_sessions
from twisted.internet import task, reactor, defer, protocol
from onDemand.utils import mpris_decode,\
    mpristime_to_upnptime,\
    upnptime_to_mpristime,\
    Timer,\
    get_default_v4_address
from tracklist import Tracklist
from default import Default
from onDemand.utils import show, stringify

log = Logger()


class Mpris_factory(Default):

    mimetypes = ["audio/mpeg", "audio/x-mpeg", "video/mpeg", "video/x-mpeg",
                 "video/mpeg-system", "video/x-mpeg-system", "video/mp4",
                 "audio/mp4", "video/x-msvideo", "video/quicktime",
                 "application/ogg", "application/x-ogg", "video/x-ms-asf",
                 "video/x-ms-asf-plugin", "application/x-mplayer2",
                 "video/x-ms-wmv", "audio/wav", "audio/x-wav", "audio/3gpp",
                 "video/3gpp", "audio/3gpp2", "video/3gpp2", "video/divx",
                 "video/flv", "video/x-flv", "video/x-matroska",
                 "audio/x-matroska"]

    def __init__(self, program='', net_type='lan', args=None, **kwargs):

        #         self.playername = program
        self.name = 'MprisPlayer'
        self.bus = None
        self.addrs = None
        self.sources = ['Playlist']
        self.sourceindex = 0
        self.metatextcount = 0
        self.active_source = 0
        self.attributes = 'Info Time Volume'
        self.token = 0
        self.con = None
        self._state = 'pending'
        self._volume = -1
        self.max_volume = 100
        self.volumeunity = 3
        self.volumemillidbperstep = 600
        self.balance = 0
        self.balancemax = 10
        self.fade = 0
        self.fademax = 10
        self.bitdepth = 0
        self.bitrate = 0
        self.seconds = 0
        self.uri = ''
        self.is_connected = False
        self.pending = True
        self._metadata = {}
        self.metadata_str = ''
        self.metadata = {}
        self.metatext = 'mpris'
        self.songid = 0
        self.maxsongid = 0
        self._duration = 0
        self.upnp_duration = '0:00:00'
        self.reltime = '0:00:00.000'
        self._track_URI = ''
        self.repeat = False
        self.shuffle = False
        self.tracksmax = 1000
        self.mtlist = ''
        self.timer = None
        self._next = False
        self.idArray = ''
        self.detailscount = 0
        self.trackcount = 0
        self.wait_list = []
        self.start_callbacks = []
        self.launched = False
        self._managed = True
        self.timeout = None
#         self.playername = 'vlc'  # testing on pc...
        self.playername = program
        self.net_type = net_type
        self.errors = 0
        self.properties = None
        self.player = None
        self.tracklist = Tracklist()
        self._muted = False
        self.connecting = True
        self.pos_event = task.LoopingCall(
            self.changed_state, {'Position': self.seconds})
        self._sources = [OrderedDict(sorted(
            {'Name': '_'.join((self.name, n)),
             'Type': n,
             'Visible': True}.
            items(), key=lambda t: t[0])) for n in self.sources]
        self.sourcexml = dict2xml(
            {'SourceList': [{'Source': n} for n in self._sources]})
        self.protocolinfo = self.mtlist = 'http-get:*:' + ''\
            .join([':*,http-get:*:'.join(self.mimetypes)]) + ':*'
        if 'cmd' in kwargs:
            if args:
                #                 print(args)
                self.process_args = [kwargs['cmd']] + [
                    arg for arg in args.split()]
            else:
                self.process_args = [kwargs['cmd']]
            self.process_path = kwargs['cmd']
        self.process = PlayerProcess(self)
        log.info("Starting Mpris Module(%s)" % self.playername)
        self.is_process()

    def launch_process(self, uri=None):
        if self.timeout is None:
            self.timeout = task.deferLater(reactor, 10, self.startup_expired)
            self.timeout.addErrback(
                lambda fail: log.debug('Timeout Cancelled'))
        d = defer.Deferred()
        if not self.launched:
            log.debug('launching player: %s'
                      % stringify(self.process_args +
                                  [self._track_URI if not uri else uri]))
            if self._volume > 0:
                volmb = str(2000.0 * math.log10(self._volume))
            else:
                volmb = '0'
            reactor.spawnProcess(  # @UndefinedVariable
                self.process,
                self.process_path,
                tuple(self.process_args + ['--vol'] + [volmb] +
                      [self._track_URI if not uri else uri]),
                env=os.environ,
                usePTY=True)
            self._managed = True
#         else:
#             self.wait_list.append(('player', 'play'), uri, None)
        self.start_callbacks.append(d)
        return d

    def is_process(self, test=False):

        for proc in psutil.process_iter():
            if proc.name() == self.playername:
                log.debug('Player process found')
                self._managed = False
                self.extpid = proc.pid
                self.juststarted = False
                self.launched = True
                if not test:
                    return self.connect()
                if test:
                    if self.errors > 5:
                        try:
                            self.protocol.shutdown()
                        except:
                            proc.kill()
                        return False
                    else:
                        self.errors += 1
                        return True
                break
        else:
            self._managed = True
            if test:
                return False

    def purge_actions(self):
        for i in range(len(self.wait_list)):  # @UnusedVariable
            action = self.wait_list.pop(0)
            md = defer.maybeDeferred(
                getattr(getattr(self, action[0][0]), action[0][1]), *action[1])
            if action[2] is not None:
                md.addBoth(lambda res: action[2].callback(res))

    def startup_expired(self):

        for clbk in self.start_callbacks:
            clbk.errback(DefaultException('Timeout'))
        self.start_callbacks = []
        self.wait_list = []

    def connected(self, con, startup=True):
        log.debug('connected: %s' % con)
        self.con = con
        self.bus = con.con
        self.errors = 0

        def got_properties(proxy):
            d = self.player.get_proxy()
            d.addCallback(got_player)
            return d

        def got_player(proxy):
            if startup:
                self.con.watch_process(
                    'org.mpris.MediaPlayer2.' + self.playername,
                    self.connection_lost)
            self.pending = False
            p = self.properties.Get('org.mpris.MediaPlayer2.Player',
                                    'PlaybackStatus')
            p.addCallbacks(
                lambda status: self.changed_state({"PlaybackStatus": status}),
                self.call_failed, errbackArgs=("Get PlaybackStatus",))
            if self._volume >= 0:
                self.r_set_volume(self._volume * 50)
            else:
                v = self.properties.Get('org.mpris.MediaPlayer2.Player',
                                        'Volume')
                v.addCallbacks(
                    lambda vol: self.changed_state({'Volume': vol}),
                    self.call_failed, errbackArgs=("Get Volume",))
            self.changed_state({'LoopStatus': 'Playlist'}),
            reactor.callLater(6,  # @UndefinedVariable
                              lambda: setattr(self, 'polling', True))
            reactor.callLater(  # @UndefinedVariable
                7, self.poll_status)
            if startup:
                t = self.tracklist.update(None, True)
            else:
                t = self.tracklist.update()
            t.addCallback(
                lambda ignored: setattr(self, "connecting", False))
            t.addCallback(
                lambda ignored: self.purge_actions())
            if self.timeout:
                self.timeout.cancel()
            for clbk in self.start_callbacks:
                clbk.callback(True)
            self.start_callbacks = []
            self.timeout = None
            return t
        if not self._managed or self.launched:
            if not self.properties:
                self.properties = ODbusProxy(
                    self.bus,
                    bus_name='org.mpris.MediaPlayer2.' + self.playername,
                    object_path='/org/mpris/MediaPlayer2',
                    interface='org.freedesktop.DBus.Properties',
                    callback_fct=self.got_event,
                    timeout=5)
                self.player = ODbusProxy(
                    self.bus,
                    bus_name='org.mpris.MediaPlayer2.' + self.playername,
                    object_path='/org/mpris/MediaPlayer2',
                    interface='org.mpris.MediaPlayer2.Player',
                    timeout=5)
                if self.tracklist is None:
                    self.tracklist = Tracklist(
                        self.bus,
                        bus_name='org.mpris.MediaPlayer2.' + self.playername,
                        object_path='/org/mpris/MediaPlayer2',
                        interface='org.mpris.MediaPlayer2.TrackList',
                        callback_fct=self.got_event,
                        timeout=5)
                    self.tracklist.parent = self

                d = self.properties.get_proxy()
            else:
                return got_player(None)
            d.addCallback(got_properties)
            return d

    def connection_lost(self, *args, **kwargs):
        log.debug('connection lost')
        # for arg in args:
        # log.error(arg)
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
                log.debug('launched')
                self.connect()
            else:
                log.debug('not launched')
                self.launched = False
                self.addrs = None
                self.properties = None
                self.player = None
                self.polling = False
                self.changed_state({'PlaybackStatus': 'Stopped'})
                self.timer = None
                self.seconds = 0
                self.reltime = '0:00:00.000'
            #self.changed_state({'PlaybackStatus': 'Stopped'})

    def call_failed(self, err, name=''):
        self.pending = False
        log.warn("Call %s failed: %s" % (name, err.getErrorMessage()))

    def connect(self, err=None):
        log.debug('connect')
        if self.is_process(True):
            if not self.bus:
                if not self.addrs:
                    self.addrs = get_user_sessions()
                    log.debug(
                        "dbus session address: %s" % stringify(self.addrs))
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
                return self.connected(self.con)
        log.warn("No process found")

    def poll_status(self):
        if self.polling:
            if not self.pending:
                if self.process.launched:
                    self.pending = True
                    if self._state == 'Playing':
                        d = self.properties.Get(
                            "org.mpris.MediaPlayer2.Player", "Position")
                        d.addCallbacks(self.update_position, self.call_failed,
                                       errbackArgs=(
                                           "Properties Get Player Position",))
                    else:
                        d = self.properties.Get(
                            "org.mpris.MediaPlayer2.Player", "PlaybackStatus")
                        d.addCallbacks(lambda state: self.changed_state({"PlaybackStatus": state}),
                                       self.call_failed,
                                       errbackArgs=(
                                           "Properties Get PlaybackStatus",))
                    d.addCallback(
                        lambda ignored: setattr(self, 'pending', False))
            reactor.callLater(5, self.poll_status)  # @UndefinedVariable

    def got_event(self, *args, **kwargs):
        log.debug("Event from %s: %s" % (str(args[1][0]),
                                         ';'.join(
            k + ': ' + stringify(v) for k, v in args[1][1].items())))
        if args[0][0] == 'properties':
            if args[1][0] == 'org.mpris.MediaPlayer2.Player':
                self.changed_state(args[1][1])
            elif args[1][0] == 'org.mpris.MediaPlayer2.TrackList':
                self.tracklist.changed_tracks()
        elif args[0][0] == 'tracklist':
            self.tracklist.changed_tracks()

    def update_position(self, pos):
        if self._state in ('Paused', 'Stopped'):
            # log.debug('del timer')
            self.seconds = int(pos) / 1000000
            self.timer = None
        elif self.timer:
            # log.debug('timer alive')
            self.timer.set(int(pos) / 1000000)
        else:
            self.seconds = int(pos) / 1000000

    def changed_state(self, *args, **kwargs):
        for arg in args:
            log.debug("New State: %s" % ';'.join(
                k + ': ' + str(v) for k, v in arg.items()))
            if isinstance(arg, dict):
                if 'PlaybackStatus' in arg:
                    if self._state != arg['PlaybackStatus']:
                        self._state = arg['PlaybackStatus']
                        self.upnp_eventAV(
                            self.event_msg[self._state][0], 'TransportState')
                        self.oh_eventPLAYLIST(
                            self.event_msg[self._state][1], 'transportstate')
                        if self._state in ('Playing', 'Paused',):
                            if self._state == 'Playing':
                                self.timer = Timer()
                            d = self.properties.Get(
                                'org.mpris.MediaPlayer2.Player',
                                'Position')
                            d.addCallback(self.update_position)
                            if not self.tracklist.tracks:
                                #                                 self.metadata = self.tracklist._playlist[
                                #                                     self.tracklist.playlist.index(self.songid)
                                # if self.songid != 0 else 0][2]
                                if self.songid == 0:
                                    self.metadata = self.tracklist._playlist[
                                        0][2]
                                    self.metadata_str = self.tracklist._playlist[
                                        0][3]
                                self.changed_track()
#                             elif self.metadata_str == '':
#                                 d.addCallback(
#                                     lambda ignored:
#                                         self.properties.Get(
#                                             'org.mpris.MediaPlayer2.Player',
#                                             "Metadata"))
#                                 d.addCallback(self.update_metadata)
                            return d
                if 'Volume' in arg:
                    if self._volume != arg['Volume']:
                        self._volume = arg['Volume']
                        self.upnp_eventRCS(int(self._volume * 50), 'Volume')
                        self.oh_eventVOLUME(int(self._volume * 50), 'volume')
                if 'Metadata' in arg:
                    log.debug('Got new md !!!!!!!!!!!!!!!!!!')
#                     self.update_metadata(arg['Metadata'])
                if 'LoopStatus' in arg:
                    self.tracklist.repeat = True if\
                        arg['LoopStatus'] == 'Playlist' else False
                    if not self.shuffle:
                        self.upnp_eventAV(
                            'REPEAT_ALL' if self.tracklist.repeat else 'NORMAL',
                            'currentplayMode')
                    else:
                        self.upnp_eventAV('REPEAT_ALL SHUFFLE' if self.repeat
                                          else 'NORMAL SHUFFLE',
                                          'currentplaymode')
                    self.oh_eventPLAYLIST(self.tracklist.repeat, 'repeat')

    def changed_track(self):
        songid = False
        try:
            idx = self.tracklist.tracks[self.metadata['trackid']][0]
        except KeyError:
            # Tracklist empty
            d = self.tracklist.update()
            d.addCallback(lambda ignored: self.changed_track)
            return d
        except TypeError:
            #  Tracklist not yet initialized
            if self.tracklist.playlist is not None:
                try:
                    idx = self.tracklist.playlist.index(
                        int(self.metadata['trackid'])) + 1
                except ValueError:
                    idx = 1
            else:
                return task.deferLater(reactor, 1, self.changed_track)
        if idx and self.songid != idx:
            songid = idx
        if songid:
            log.debug("new track: %s" % str(songid))
            self.songid = songid
            self.trackcount += 1
            self.upnp_eventAV(int(self.songid), 'CurrentTrack')
            self.oh_eventPLAYLIST(int(self.songid), 'id')
            self.oh_eventTIME(self.trackcount, 'trackcount')
            if self.tracklist.tracks:
                print(self.tracklist.tracks)
#             self.tracklist.tracks[songid][1].update(self.metadata)
                self.metadata = self.tracklist.tracks[songid][1]
#             else:
#                 self.metadata = self.tracklist._playlist[songid - 1][2]

        if 'duration' in self.metadata:
            if self._duration != self.metadata['duration']:
                duration = int(self.metadata['duration'])
                log.debug('duration: %d' % duration)
                if duration < 1:
                    self.upnp_duration = "0:00:00"
                    self._duration = 0
                else:
                    self._duration = duration
                    self.upnp_duration = mpristime_to_upnptime(duration)
                log.debug('track length: %s'
                          % self.upnp_duration)
                self.upnp_eventAV(self.upnp_duration,
                                  'CurrentTrackDuration')
                self.oh_eventINFO(int(self._duration // 1000000), 'duration')
                self.oh_eventTIME(int(self._duration // 1000000), 'duration')
        if 'url' in self.metadata:
            if self._track_URI != self.metadata['url']:
                self._track_URI = self.metadata['url']
                self.upnp_eventAV(self._track_URI, 'AVTransportURI')
                self.oh_eventINFO(self._track_URI, 'uri')
                self.upnp_eventAV(self._track_URI, 'CurrentTrackURI')
        if 'artUrl' in self.metadata:
            url = self.parent.register_art_url(self.metadata['artUrl'])
            self.metadata['albumArtURI'] = url
        self.oh_eventINFO(self.metadata_str.encode('utf-8'), 'metadata')
        self.upnp_eventAV(
            self.metadata_str.encode('utf-8'), 'AVTransportURIMetaData')

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
            s = int(self.timer.get())
#             if (self._duration // 1000000 - s) < 2:
#                 if not self._next:
#                     log.debug('next!!')
#                     self._next = True
#                     reactor.callLater(3, self.next)  # @UndefinedVariable
            log.debug("time: %s" % str(s))
            if fmt == 'UPNP':
                return mpristime_to_upnptime(s)
            else:
                return s
        else:
            if fmt == 'UPNP':
                return self.reltime
            else:
                log.debug("time: %s" % str(self.seconds))
                return self.seconds

    def set_songid(self, songid):
        self.songid = songid['Id']
        return self.songid

    def set_track_URI(self, uri, md=''):
        log.debug("set track uri: \"%s\"" % uri)
        try:
            log.debug("current uri : %s " %
                      self._track_URI)
        except:
            pass
        if uri != self._track_URI:
            self._track_URI = uri
            self.metadata_str = md
            self.timer = Timer()
            if not self.launched:
                self.wait_list.append((
                    ('tracklist', 'insert'), (-1, uri, md, False), None))
                self.launch_process()
                return
            t = self.tracklist.insert(-1,
                                      uri, md, True)
            t.addCallback(show, 'New Id')
#             if self.tracks:
#                 d = self.insert(
#                     uri, '/org/mpris/MediaPlayer2/TrackList/NoTrack' if len(
#                         self.tracks) == 0 else self.tracks[-1],
#                     md,
#                     current=True)
#             else:
#                 d = self.insert(uri, len(self.playlist), md, current=True)
#                 d.addCallback(self.set_songid)
            # self.changed_state({'Metadata': md.encode('utf-8')})

    def set_position(self, newpos, fmt='UPNP'):
        if self.process.launched:
            def transition(obj, state):
                log.debug(str(obj))
                self.changed_state({'PlaybackStatus': state})
            if fmt == 'UPNP':
                newtime = upnptime_to_mpristime(newpos)
                offset = newtime - self.seconds
            else:
                offset = (float(newpos) - float(self.seconds)) * 1000000
            current_state = self._state
            self.changed_state({'PlaybackStatus': 'Pending'})
            d = self.player.Seek(offset)
            d.addCallbacks(transition, self.call_failed,
                           callbackArgs=(current_state,),
                           errbackArgs=("Seek",))
            return d

    def set_repeat(self, repeat):
        log.debug('repeat=%s' % repeat)
        self.repeat = repeat
        self.oh_eventPLAYLIST(self.repeat, 'repeat')

    def set_shuffle(self, shuffle):
        self.shuffle = shuffle

    def volUp(self):
        if self._volume == 0:
            vol = self.get_volume()
            try:
                newvol = vol + 5
            except:
                newvol = self._volume * 100 + 5
            return self.set_volume('Master', newvol)
        else:
            if self._volume > 95:
                return
            newvol = self._volume * 100 + 5
            return self.set_volume('Master', newvol)

    def volDown(self):
        if self._volume > 0.05:
            newvol = self._volume * 100 - 5
            return self.set_volume('Master', newvol)
        else:
            self._volume = 0
            return self.set_volume('Master', 0)

    def playpause(self):
        if self._state != "Playing":
            return self.r_play()
        return self.r_pause()

    '''
    UPNP wrapped functions
    '''
    # onDemand vendor method

    def r_get_room(self):
        return self.room

    '''
    AVTransport and OpenHome Playlist
    '''

    def r_delete_all(self):
        log.debug('DeleteAll')
        if self.tracklist:
            return self.tracklist.clear()

    def r_delete_id(self, value):
        log.debug('DeleteID: %s' % str(value))
        if self.tracklist:
            return self.tracklist.delete(value)

    def r_get_current_transport_actions(self, instanceID):
        log.debug('GetCurrentActions')
        return self.get_transport_actions()

    def r_get_media_info(self, instanceID):
        log.debug('GetMediaInfo')
        if self.tracklist:
            if self.tracklist.tracks:
                return (str(len(self.tracklist.tracklist)),
                        self.get_track_duration(), self.get_track_URI(),
                        self.get_track_md(), '', '', 'UNKNOWN', 'UNKNOWN',
                        'UNKNOWN',)
            return (str(len(self.tracklist.playlist)),
                    self.get_track_duration(), self.get_track_URI(),
                    self.get_track_md(), '', '', 'UNKNOWN', 'UNKNOWN',
                    'UNKNOWN',)
        return ('0', self.get_track_duration(), self.get_track_URI(),
                self.get_track_md(), '', '', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN',)

    def r_get_media_info_ext(self, instanceID):
        log.debug('GetMediaInfoExt')
        if self.tracklist:
            if self.tracklist.tracks:
                return (str(len(self.tracklist.tracklist)), 'TRACK_AWARE',
                        self.get_track_duration(), self.get_track_URI(),
                        self.get_track_md(), '', '', 'UNKNOWN', 'UNKNOWN',
                        'UNKNOWN',)
            else:
                return (str(len(self.tracklist.playlist)), 'TRACK_AWARE',
                        self.get_track_duration(), self.get_track_URI(),
                        self.get_track_md(), '', '', 'UNKNOWN', 'UNKNOWN',
                        'UNKNOWN',)

    def r_get_position_info(self, instanceID):
        log.debug('GetPositionInfo')
        if self.player:
            return (self.player.get_track(), self.get_track_duration(),
                    self.get_track_md(), self.player.get_track_URI(),
                    self.player.get_reltime(), self.player.get_abstime(),
                    self.player.get_relcount(), self.player.get_abscount(),)

    def r_get_transport_info(self, instanceID):
        log.debug('GetTransportInfo')
        return (self.get_state(), 'OK', self.get_rate(),)

    def r_id(self):
        log.debug('Id')
        if self.player:
            if self.songid == 0:
                d = self.properties.Get(
                    "org.mpris.MediaPlayer2.Player", "Metadata")
                d.addCallback(lambda md: self.changed_state({"Metadata": md}))
                d.addCallback(lambda ignored: self.songid)
                return d
        return self.songid

    def r_id_array(self):
        log.debug('IdArray')
        return (self.token, self.idArray,)

    def r_id_array_changed(self, token):
        log.debug('IdArrayChanged: %s' % token)
        if token != self.token:
            return 1
        return 0

    def r_insert(self, afterid, url, md=''):
        log.debug(' Remote Insert: %s' % " ".join((str(afterid), url, md,)))
        if self.tracklist:
            return self.tracklist.insert(afterid, url, md)
        else:
            self.set_track_URI(url, md)
            return '1'

    def r_next(self, instanceID=0):
        log.debug("next: %s" % str(self.songid))
        if self.tracklist:
            tid = self.tracklist.next(self.songid)
            if tid is not None:
                self.r_play(songid=tid)

    def r_play(self, instanceID=0, speed=1, songid=None,
               ignored=None):

        log.debug('Play: %s' % str(songid))

        if songid is not None:
                #                 log.err(songid)
            if self.tracklist:
                if self.tracklist.tracks is not None:
                    if self.playername == 'vlc' and\
                            self.tracklist.tracks[songid][0].startswith('***'):
                        id_pos = self.tracklist.tracklist.index(songid)
                        if id_pos > 0:
                            afterid = self.tracklist.tracklist.pop(id_pos - 1)
                        else:
                            self.tracklist.tracklist.pop(0)
                            afterid = 0
                        self.tracklist.insert(afterid,
                                              self.tracklist.tracks[
                                                  songid][0][3:],
                                              '',
                                              True)
                        reactor.callLater(2,  # @UndefinedVariable
                                          self.tracklist.update)
                    else:
                        self.tracklist.GoTo(self.tracklist.tracks[songid][0])
                else:
                    ind = self.tracklist.playlist.index(int(songid))
                    uri = self.tracklist._playlist[ind][1]
                    self.metadata = self.tracklist._playlist[ind][2]
                    self.metadata_str = self.tracklist._playlist[ind][3]
                    if self.player:
                        d = self.player.Stop()
                        d.addErrback(self.call_failed, "Stop")
                        d.addBoth(lambda ignored:
                                  task.deferLater(reactor,
                                                  1,
                                                  self.r_play,
                                                  *(instanceID, speed, songid)))
                    else:
                        d = self.launch_process(uri)
                    d.addCallback(lambda ignored: self.changed_state(
                        {'PlaybackStatus': 'Playing'}))
                    return d
                return
        else:
            if self.player:
                d = self.player.Play()
            else:
                d = self.launch_process()
            d.addCallbacks(
                lambda ignored: self.changed_state(
                    {'PlaybackStatus': 'Playing'}),
                self.call_failed, errbackArgs=("Play",))
            return d

    def r_pause(self, instanceID=0):
        log.debug('Pause')
        if self.player:
            d = self.player.Pause()
            d.addCallbacks(
                lambda ignored: self.changed_state(
                    {'PlaybackStatus': 'Paused'}),
                self.call_failed, errbackArgs=('Pause',))

    def r_previous(self, instanceID=0):
        log.debug("Previous")
        if self.songid == 0:
            d = self.properties.Get(
                "org.mpris.MediaPlayer2.Player", "Metadata")
            d.addCallback(lambda md: self.changed_state({"Metadata": md}))
            d.addCallback(self.r_previous)
            return d
        tid = self.tracklist.next(self.songid)
        if tid is not None:
            self.r_play(songid=tid)
        tid = self.tracklist.next(self.songid, -1)
        if tid is not None:
            self.r_play(songid=tid)

    def r_protocol_info(self):
        log.debug('ProtocolInfo')
        return self.protocolinfo

    def r_read(self, value):
        log.debug('Read')
        d = self.playlist.get_track(value)
        return (d,)

    def r_read_list(self, items):
        log.debug('Readlist: %s' % items)
        if self.tracklist:
            d = self.tracklist.get_tracks(
                [int(track) for track in items.split()])
            return d
        return []

    def r_repeat(self):
        log.debug('Repeat')
        return self.repeat

    def r_record(self, instanceID):
        raise NotImplementedError()

    def r_seek(self, instanceID, unit, pos):
        log.debug('Seek: %s %s' % (unit, pos))
        self.set_position(pos)

    def r_seek_id(self, value):
        log.debug('SeekId: %s' % value)
        self.r_play(songid=value)

    def r_seek_index(self, value):
        log.debug('Seekindex')
        return self.playindex(value)

    def r_seek_second_absolute(self, value):
        log.debug('Seek Second Absolute: %s' % str(value))
        return self.set_position(value, 'SECONDS')

    def r_seek_second_relative(self, value):
        log.debug('Seek Second Relative: %s' % str(value))
        return self.set_position_relative(value, 'SECONDS')

    def r_set_repeat(self, repeat):
        self.changed_state({'repeat': str(int(repeat))})

    def r_set_shuffle(self, shuffle):
        self.changed_state({'random': str(int(shuffle))})

    def r_set_avtransport_uri(self, instanceID, uri, uri_metadata):
        log.debug('SetAVtransportURI')
        self.set_track_URI(uri, uri_metadata)

    def r_shuffle(self):
        if self.tracklist:
            return self.tracklist.shuffle
        return False

    def r_stop(self, instanceID=0):
        if self.player:
            self.player.Stop()
        else:
            self.protocol.shutdown()

    def r_tracks_max(self):
        return self.tracksmax

    def r_transport_state(self, instanceID=0):
        if 'Source' in self.parent.deviceType:
            return self.event_msg[self._state][1]
        return self.event_msg[self._state][0]

    '''
    OpenHome Info
    '''

    def r_counters(self):
        return (self.trackcount, self.detailscount, self.metatextcount,)

    def r_track(self):
        return (self._track_URI, self.metadata_str,)

    def r_details(self):
        return (
            self.ohduration, self.bitrate, self.bitdepth,
            self.samplerate, self.lossless, self.codecname,)

    def r_metatext(self):
        return self.metatext

    '''
    Rendering Control and Open Home Volume
    '''

    def r_volume(self):
        return self._volume * 50

    def r_set_volume(self, volume, channel=0):
        self.properties.Set('org.mpris.MediaPlayer2.Player',
                            "Volume", float(volume / 50.00))
        d = task.deferLater(reactor, 0.5, self.properties.Get,
                            *('org.mpris.MediaPlayer2.Player', 'Volume'))
        d.addCallback(lambda vol: self.changed_state({'Volume': vol}))

    def r_volume_inc(self):
        self.r_set_volume((self._volume * 50) + 5)

    def r_volume_dec(self):
        if self._volume > 0.05:
            self.r_set_volume((self._volume * 50) - 5)

    def r_volume_limit(self):
        return self.max_volume

    def r_balance(self):
        return self.balance

    def r_fade(self):
        return self.fade

    def r_balance_inc(self):
        # TODO
        self.balance += 1

    def r_balance_dec(self):
        # TODO
        self.balance -= 1

    def r_set_fade(self, value):
        # TODO
        self.fade = int(value)

    def r_fade_inc(self):
        # TODO
        self.fade += 1

    def r_fade_dec(self):
        # TODO
        self.fade -= 1

    def r_mute(self):
        return self._muted

    def r_set_mute(self, mute):
        if mute is not self._muted:
            self._muted = mute
            if mute:
                self.old_vol = self._volume
                self.r_set_volume(0)
            else:
                self.r_set_volume(self.old_vol)

    def r_characteristics(self):
        return self.max_volume, self.volumeunity, self.max_volume,\
            self.volumemillidbperstep, self.balancemax, self.fademax

    '''
    OpenHome Time
    '''

    def r_time(self):
        return (self.trackcount, self._duration / 1000000,
                self.get_reltime('seconds'))

    '''
    OpenHome Product
    '''

    def r_manufacturer(self=None):
        log.debug('Manufacturer from Product')
        return (self.parent.manufacturer,
                self.parent.manufacturerInfo, self.parent.manufacturerURL,
                ''.join((self.parent.getLocation(get_default_v4_address()),
                         '/pictures/icon.png')),)

    def r_model(self=None):
        log.debug('Model from Product')
        return (self.parent.modelName, self.parent.modelDescription,
                self.parent.manufacturerURL,
                ''.join((self.parent.getLocation(get_default_v4_address()),
                         '/pictures/', self.parent.modelName, '.png',)))

    def r_product(self):
        log.debug('Product from Product')
        return self.room, self.parent.modelName, self.parent.modelDescription,\
            self.parent.manufacturerURL,\
            ''.join((self.parent.getLocation(get_default_v4_address()),
                     '/pictures/', self.parent.modelName, '.png',))

    def r_standby(self):
        log.debug('Standby from Product')
        return self.standby

    def r_set_standby(self, val=None):
        log.debug('SetStandby from Product')
        if val is None:
            return self.standby
        raise NotImplementedError()

    def r_source_count(self):
        log.debug('SourceCount from Product')
        return len(self.sources)

    def r_source_xml(self, *args, **kwargs):
        log.debug('SourceXml from Product')
        return self.sourcexml
# return dict2xml({'SourceList': [{'Source': n} for n in self.sources]})

    def r_source_index(self):
        log.debug('SourceIndex from Product')
        return self.sourceindex

    def r_set_source_index(self, idx=None):
        log.debug('SetSourceIndex from Product')
        if idx is None:
            return self.sourceindex
        else:
            try:
                self.sourceindex = int(idx)
                self.oh_product_event('sourceindex', self.sourceindex)
            except:
                for i, source in enumerate(self.sources.keys()):
                    if source['Name'] == idx:
                        self.sourceindex = i
                        self.oh_product_event('sourceindex', self.sourceindex)
                        return
                    log.critical('Unknown Source: %s' % idx)

    def r_set_source_index_by_name(self, value):
        log.debug('SetSourceIndexByName from Product')
        return self.set_source_index(value)

    def r_source(self, idx):
        idx = int(idx)
        return (self.parent.sources[idx].friendlyName,
                self.parent.sources[idx].type, True,
                self.parent.sources[idx].name,)

    def r_attributes(self):
        return self.attributes

    def r_source_xml_change_count(self):
        raise NotImplementedError()


class PlayerProcess(protocol.ProcessProtocol):
    '''
    Manage player process
    '''
    launched = False

    def __init__(self, parent):
        self.parent = parent
        parent.protocol = self
        self.data = ''

    # Will get called when the subprocess has data on stdout
#     def outReceived(self, data):
#         log.warn('STDOUT: %s' % data)

    # Will get called when the subprocess has data on stderr
    def errReceived(self, data):
        log.warn('Subprocess STDERR: %s' % data)

    def connectionMade(self):
        #         self.transport.closeStdin()
        reactor.callLater(1, self.parent.connect)  # @UndefinedVariable
        self.launched = True
        log.info('process started')

    def processEnded(self, reason):
        log.debug('process ended')
        if reason.value.exitCode != 0:
            log.warn("processEnded, status %s" % reason.value.exitCode)
        self.launched = False
        self.parent.connection_lost(really_lost=True)

    def shutdown(self):
        self.transport.loseConnection()
