# encoding: utf-8
'''
Created on 29 oct. 2016

@author: Bertrand Verdu
'''
from collections import OrderedDict
from twisted.application.service import Service
from twisted.logger import Logger
from upnpy_spyne.utils import didl_decode, dict2xml, didl_encode
from onDemand.protocols.dbus import ODbusProxy
from twisted.internet import task, reactor
from onDemand.utils import mpris_decode,\
    mpristime_to_upnptime,\
    upnptime_to_mpristime,\
    Timer
from onDemand.plugins.mediaplayer import MediaPlayer
from tracklist import Tracklist, MprisTracklist
from onDemand.utils import show, stringify

log = Logger()


class Default(Service, MediaPlayer):
    name = 'MprisPlayer'
    bus = None
    addrs = None
    con = None

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

        self.playername = program
        self.token = 0
        self.net_type = net_type
        self.errors = 0
        self.properties = None
        self.player = None
        self.tracklist = Tracklist()
        self.tracklist.parent = self
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
        log.info("Starting Mpris: %s" % self.playername)

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
            p.addCallback(lambda status: self.changed_state(
                {"PlaybackStatus": status}))
            v = self.properties.Get('org.mpris.MediaPlayer2.Player',
                                    'Volume')
            v.addCallback(lambda vol: self.changed_state({'Volume': vol}))
            r = self.properties.Get('org.mpris.MediaPlayer2.Player',
                                    'LoopStatus')
            r.addCallback(lambda loop: self.changed_state(
                {'LoopStatus': loop}))
            if startup:
                t = self.test_tracklist.get_proxy()
                t.addCallback(
                    self.test_tracklist.update)
                t.addCallbacks(lambda ignored: setattr(
                    self, 'tracklist', self.test_tracklist),
                    lambda ignored: log.info(
                        "Local Tracklist used, reason: %s"
                        % ignored.getErrorMessage))
            else:
                t = self.tracklist.update()
            t.addCallback(
                lambda ignored: setattr(self, "connecting", False))
            return t

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
            self.test_tracklist = MprisTracklist(
                self.bus,
                bus_name='org.mpris.MediaPlayer2.' + self.playername,
                object_path='/org/mpris/MediaPlayer2',
                interface='org.mpris.MediaPlayer2.TrackList',
                callback_fct=self.got_event,
                timeout=5)
            self.test_tracklist.parent = self

            d = self.properties.get_proxy()
        else:
            return got_player(None)
        d.addCallback(got_properties)
        return d

    def connection_lost(self, *args, **kwargs):

        # for arg in args:
        # log.err(arg)
        if self.properties is not None and not self.connecting:
            log.error('connection lost')
            self.errors += 1
            if self.errors < 5:
                self.connect()
            else:
                log.error('max error count reached aborting')
                self.seconds = 0
                self.reltime = '0:00:00.000'
                self.changed_state({'PlaybackStatus': 'Stopped'})

    def call_failed(self, err, name=''):
        self.pending = False
        log.warn("Call %s failed: %s" % (name, err.getErrorMessage()))

    def connect(self, err=None):
        log.debug('connecting')
        self.connecting = True
        if not self.bus:
            return self.con.connect(self)
        else:
            return self.connected(self.con, False)

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
                            if not self.tracklist.connected:
                                if self.songid == 0:
                                    try:
                                        self.metadata = self.tracklist.tracks[
                                            self.tracklist.tracklist[0]][2]
                                        self.metadata_str = self.tracklist.tracks[
                                            self.tracklist.tracklist[0]][3]
                                    except IndexError:
                                        reactor.callLater(  # @UndefinedVariable
                                            2, self.changed_state, *args,
                                            **kwargs)
                                self.changed_track()
                            elif self.metadata_str == '':
                                d.addCallback(
                                    lambda ignored:
                                        self.properties.Get(
                                            'org.mpris.MediaPlayer2.Player',
                                            "Metadata"))
                                d.addCallback(self.update_metadata)
                            return d
                if 'Volume' in arg:
                    if self._volume != arg['Volume']:
                        self._volume = arg['Volume']
                        self.upnp_eventRCS(int(self._volume * 50), 'Volume')
                        self.oh_eventVOLUME(int(self._volume * 50), 'volume')
                if 'Metadata' in arg:
                    self.update_metadata(arg['Metadata'])
                if 'LoopStatus' in arg:
                    self.tracklist.repeat = True if\
                        arg['LoopStatus'] == 'Playlist' else False
                    if not self.tracklist.shuffle:
                        self.upnp_eventAV(
                            'REPEAT_ALL' if self.tracklist.repeat
                            else 'NORMAL', 'currentplayMode')
                    else:
                        self.upnp_eventAV('REPEAT_ALL SHUFFLE' if self.repeat
                                          else 'NORMAL SHUFFLE',
                                          'currentplaymode')
                    self.oh_eventPLAYLIST(self.tracklist.repeat, 'repeat')

    def changed_track(self):
        songid = False
        idx = False
        try:
            idx = self.tracklist.tracks[self.metadata['trackid']][0]
        except KeyError:
            # Tracklist empty
            if self.tracklist.connected:
                d = self.tracklist.update()
                d.addCallback(lambda ignored: self.changed_track)
                return d
        except TypeError:
            #  Tracklist not yet initialized
            return task.deferLater(reactor, 1, self.changed_track)
        if idx and self.songid != idx:
            songid = idx
        if songid:
            log.debug("new track: %s" % str(songid))
#             print(self.metadata)
            self.songid = songid
            self.trackcount += 1
            self.upnp_eventAV(int(self.songid), 'CurrentTrack')
            self.oh_eventPLAYLIST(int(self.songid), 'id')
            self.oh_eventTIME(self.trackcount, 'trackcount')
            self.metadata.update(self.tracklist.tracks[songid][1])

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
        self.oh_eventINFO(self.metadata_str, 'metadata')
        self.upnp_eventAV(self.metadata_str, 'AVTransportURIMetaData')

    def update_metadata(self, metadata):
        log.debug("New md: %s" % stringify(metadata))
        if isinstance(metadata, dict):
            log.debug('dico...')
            if self._metadata == metadata:
                return
            else:
                self._metadata = metadata
                self.metadata = mpris_decode(metadata)
                self.metadata_str = didl_encode(self.metadata)
        elif isinstance(metadata, str):
            log.debug('string...')
            if self.metadata_str == metadata:
                return
            else:
                self.metadata_str = metadata
                self.metadata = didl_decode(metadata)
                log.debug(self.metadata)
        else:
            log.error('Bad metadata format : %s' % metadata)
            return
        if 'trackid' in self.metadata:
            self.changed_track()

    def get_track_duration(self):
        try:
            duration = self._track_duration
        except:
            duration = '00:00:00'
        return duration

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
#             log.debug("time: %s" % str(s))
            if fmt == 'UPNP':
                return mpristime_to_upnptime(s)
            else:
                return s
        else:
            if fmt == 'UPNP':
                return self.reltime
            else:
                #                 log.debug("time: %s" % str(self.seconds))
                return self.seconds

    def set_track_URI(self, uri, md=''):
        log.debug("set track uri : %s " % uri)
        try:
            log.debug("current uri : %s " %
                      self._track_URI)
        except:
            pass
        if uri != self._track_URI:
            self._track_URI = uri
            self.metadata_str = md
#                 self.set_metadata(didl_decode(md.encode('utf-8')))
            self.timer = Timer()
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

        def transition(obj):
            current_state = self._state
            self.changed_state({'PlaybackStatus': 'Pending'})
            reactor.callLater(  # @UndefinedVariable
                0.5,
                self.changed_state,
                {'PlaybackStatus': current_state})
        if fmt == 'UPNP':
            newtime = upnptime_to_mpristime(newpos)
            offset = (newtime - self.seconds) * 1000000
        else:
            offset = int((float(newpos) - float(self.seconds)) * 1000000)
        d = self.player.Seek(offset)
        d.addCallbacks(transition, self.call_failed)
        return d

    def set_position_relative(self, pos, fmt='UPNP'):

        def transition(obj):
            current_state = self._state
            self.changed_state({'PlaybackStatus': 'Pending'})
            reactor.callLater(  # @UndefinedVariable
                0.5,
                self.changed_state,
                {'PlaybackStatus': current_state})
        if fmt == 'UPNP':
            offset = upnptime_to_mpristime(pos) * 1000000
        else:
            offset = int((float(pos)) * 1000000)
        d = self.player.Seek(offset)
        d.addCallbacks(transition, self.call_failed)
        return d

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

    def play(self, speed=1, songid=None):

        log.debug('entering play...')

        if songid is not None:
                #                 log.err(songid)
            if self.tracklist.connected:
                if self.playername == 'vlc' and\
                        self.tracklist.tracks[songid][0].startswith('***'):
                    id_pos = self.tracklist.tracklist.index(songid)
                    if id_pos > 0:
                        afterid = self.tracklist.tracklist.pop(id_pos - 1)
                    else:
                        self.tracklist.tracklist.pop(0)
                        afterid = 0
                    self.tracklist.insert(afterid,
                                          self.tracklist.tracks[songid][0][3:],
                                          '',
                                          True)
                    reactor.callLater(2,  # @UndefinedVariable
                                      self.tracklist.update)
                else:
                    self.tracklist.GoTo(self.tracklist.tracks[songid][0])
            else:
                self.player.OpenUri(self.tracklist.tracks[songid][1])
        else:
            self.player.Play()

    '''
    UPNP wrapped functions
    '''

    '''
    AVTransport and OpenHome Playlist
    '''

    def r_id(self):
        if self.songid == 0:
            d = self.properties.Get(
                "org.mpris.MediaPlayer2.Player", "Metadata")
            d.addCallback(lambda md: self.changed_state({"Metadata": md}))
            d.addCallback(lambda ignored: self.songid)
        return self.songid

    def r_next(self, instanceID=0):
        log.debug("next")
        if self.songid == 0:
            self.songid = -1
            if self.tracklist.connected:
                d = self.properties.Get(
                    "org.mpris.MediaPlayer2.Player", "Metadata")
                d.addCallback(lambda md: self.changed_state({"Metadata": md}))
                d.addCallback(self.r_next)
                return d
        if self.songid == -1:
            self.songid = 0
            return
        tid = self.tracklist.next(self.songid)
        if tid is not None:
            self.play(songid=tid)

    def r_pause(self, instanceID=0):
        log.debug('pause')
        self.player.Pause()

    def r_previous(self, instanceID=0):
        log.debug("previous")
        if self.songid == 0:
            self.songid = -1
            if self.tracklist.connected:
                d = self.properties.Get(
                    "org.mpris.MediaPlayer2.Player", "Metadata")
                d.addCallback(lambda md: self.changed_state({"Metadata": md}))
                d.addCallback(self.r_previous)
                return d
        if self.songid == -1:
            self.songid = 0
            return
        tid = self.tracklist.next(self.songid)
        if tid is not None:
            self.play(songid=tid)
        tid = self.tracklist.next(self.songid, -1)
        if tid is not None:
            self.play(songid=tid)

    def r_read(self, value):
        log.debug('read')
        return self.tracklist.get_track(value)

    def r_read_list(self, items):
        log.debug('readlist: %s' % items)
        d = self.tracklist.get_tracks(
            [int(track) for track in items.split()])
        return d

    def r_seek(self, instanceID, unit, pos):
        log.debug('seek: %s %s' % (unit, pos))
        self.set_position(pos)

    def r_set_repeat(self, repeat):
        if self.tracklist.connected:
            d = self.properties.Set('org.mpris.MediaPlayer2.Player',
                                    'LoopStatus',
                                    'Playlist')
            return d
        else:
            self.tracklist.repeat = repeat
            self.changed_state({'repeat': str(int(repeat))})

    def r_set_shuffle(self, shuffle):
        if self.tracklist.connected:
            d = self.properties.Set('org.mpris.MediaPlayer2.Player',
                                    'LoopStatus',
                                    'Shuffle')
            return d
        else:
            self.tracklist.shuffle = shuffle
            self.changed_state({'shuffle': str(int(shuffle))})

    def r_set_avtransport_uri(self, instanceID, uri, uri_metadata):
        self.set_track_URI(uri, uri_metadata)

    def r_stop(self, instanceID=0):
        self.player.Stop()

    '''
    Rendering Control and Open Home Volume
    '''

    def r_volume(self):
        return self._volume * 100

    def r_set_volume(self, volume, channel=0):
        self.properties.Set('org.mpris.MediaPlayer2.Player',
                            "Volume", float(volume / 100.00))

    def r_volume_inc(self):
        self.r_set_volume((self._volume * 100) + 5)

    def r_volume_dec(self):
        if self._volume > 0.05:
            self.r_set_volume((self._volume * 100) - 5)

    def r_set_mute(self, mute):
        if mute is not self._muted:
            self._muted = mute
            if mute:
                self.old_vol = self._volume
                self.r_set_volume('0')
            else:
                self.r_set_volume(self.old_vol)


Mpris_factory = Default
