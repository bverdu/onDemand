# encoding: utf-8
'''
Created on 23 avr. 2015

@author: Bertrand Verdu
'''
import os
from collections import OrderedDict
from lxml import etree as et
from twisted.logger import Logger
from twisted.internet.protocol import ReconnectingClientFactory
# from twisted.internet.endpoints import connectProtocol
from twisted.internet import defer, reactor, utils, task
from upnpy_spyne.utils import didl_decode, didl_encode, id_array, dict2xml
from onDemand.protocols.mpd import MpdProtocol
from onDemand.utils import Timer, \
    mpd_decode, \
    mpdtime_to_upnptime, \
    upnptime_to_mpdtime, \
    get_default_v4_address
from playlist import Playlist
from onDemand.plugins import Client

log = Logger(namespace='protocol.mpd')


class Mpd_factory(ReconnectingClientFactory, Client):
    '''
    Twisted Reconnecting client factory for mpd server
    convert all UPnP and OpenHome service function to mpd remote calls
    '''

    _mtlist = ''
    _muted = True
    _rate = "1"
    _state = "pending"
    _track_duration = '0:00:00.000'
    ohduration = 0
    _track_URI = ''
    _volume = 100
    active_source = 0
    attributes = 'Info Time Volume'
    balance = 0
    balancemax = 10
    bitdepth = 0
    bitrate = 0
    cancelplay = False
    codecname = 'MP3'
    counter = 0
    detailscount = 0
    fade = 0
    fademax = 10
    idArray = ''
    lossless = False
    maxid = 0
    max_volume = 100
    metadata = {}
    metadata_str = 'NOT_IMPLEMENTED'
    metatext = ''
    metatextcount = 0
    mimetypes = ['audio/aac', 'audio/mp4', 'audio/mpeg', 'audio/mpegurl',
                 'audio/vnd.rn-realaudio', 'audio/vorbis', 'audio/x-flac',
                 'audio/x-mp3', 'audio/x-mpegurl', 'audio/x-ms-wma',
                 'audio/x-musepack', 'audio/x-oggflac', 'audio/x-pn-realaudio',
                 'audio/x-scpls', 'audio/x-speex', 'audio/x-vorbis',
                 'audio/x-wav', 'application/x-ogm-audio',
                 'audio/x-vorbis+ogg', 'audio/ogg']
    mtlist = ''
    name = "MpdPlayer"
    oh_state = 'Buffering'
    old_vol = 0
    parent = None
    reltime = '0:00:00.000'
    repeat = False
    room = 'Home'
    samplerate = 0
    seconds = 0
    shuffle = False
    songid = 0
    sources = ['Playlist']
    sourceindex = 0
    upnp_state = "TRANSITIONNING"
    volumeunity = 3
    volumemillidbperstep = 600
    timer = None
    token = 0
    trackcount = 0
    tracksmax = 0
    transport_actions = ['PLAY']
#     ohduration = 0

    def __init__(self, cover_dir, net_type='lan'):

        self.connected = False
        self.net_type = net_type
        self.proto = MpdProtocol()
        self.proto._event = self.dispatch_event
        self.status = {'state': 'stop'}
        self.playlist = Playlist(self)
        self.waiting = False
        self.calls = []
        self.cover_dir = cover_dir
        self._sources = [OrderedDict(sorted(
            {'Name': '_'.join((self.name, n)),
             'Type': n,
             'Visible': True}.
            items(), key=lambda t: t[0])) for n in self.sources]
        self.sourcexml = dict2xml(
            {'SourceList': [{'Source': n} for n in self._sources]})
        self.protocolinfo = self.mtlist = 'http-get:*:' + ''\
            .join([':*,http-get:*:'.join(self.mimetypes)]) + ':*'

    def buildProtocol(self, addr):
        return self.proto
    '''
    Internal functions
    '''

    def dispatch_event(self, events=None):

        def set_connected():
            self.connected = True
            p = self.call('plchanges', self.playlist.plsversion)
            p.addCallback(self.playlist.update)

        d = None
        for evt in events:
            if evt == 'Error':
                log.error('bad event: {name}', name=events[evt])
                return
            elif evt == 'changed':
                chg = events[evt]
            else:
                #                 log.msg(events[evt])
                return
            if chg == 'disconnected':
                self.connected = False
                continue
            if chg == 'playlist':
                log.error('update from: %s' % self.playlist.plsversion)
                d = self.call('plchanges', self.playlist.plsversion)
                d.addCallback(self.playlist.update)
            else:
                d = self.call('status')
                if chg == 'connected':
                    d.addCallback(self.filter_event)
                    reactor.callLater(1, set_connected)  # @UndefinedVariable
                elif chg == 'mixer':
                    d.addCallback(self.filter_event,
                                  'volume')
                elif chg == 'player':
                    d.addCallback(self.filter_event)
            return d

    def filter_event(self, data, filtr=None):
        if data is None:
            return
        if not isinstance(data, list):
            data = [data]
        if filtr is not None:
            for d in data:
                self.status.update(d)
            self.changed_state({filtr: self.status[filtr]})
        else:
            dic = {}
            for d in data:
                for it in d.iteritems():
                    if it not in self.status.items():
                        self.status.update(dict([it]))
                        dic.update(dict([it]))
                        if it[0] == 'playlistlength':
                            self.playlist.length = int(it[1])
            self.changed_state(dic)

    def call(self, command=None, params=None):
        #         log.error('register %s' % command)
        d = defer.Deferred()
        if command is not None:
            self.proto.addCallback(d)
        if not self.connected:
            if command:
                self.calls.append((command, params))
        else:
            if len(self.calls) > 0:
                if command:
                    self.calls.append((command, params))
                else:
                    d = None
                command, params = self.calls.pop(0)
            if params is not None:
                c = ' '.join([command, str(params)]).encode('utf-8')
            else:
                c = command.encode('utf-8')
            if self.proto.idle:
                self.proto.noidle()
            self.proto.sendLine(c)
#             log.error('send %s' % c)
            if len(self.calls) > 0:
                self.call()
        return d

    def changed_state(self, state):
        changed = state.keys()
        if 'state' in changed:
            self.set_state(state['state'])
        if "volume" in changed:
            log.debug('volume changed')
            vol = int(state['volume'])
            if vol != self._volume:
                if vol != 0:
                    self._volume = vol
                    muted = False
                else:
                    muted = True
                log.debug('send volume')
                self.oh_eventVOLUME(self._volume, 'volume')
                self.upnp_eventRCS(self._volume, 'volume')
                if muted is not self._muted:
                    self._muted = muted
                    self.upnp_eventRCS(self._muted, 'mute')
                self.oh_eventVOLUME(int(self._muted), 'mute')

        if 'songid' in changed:
            self.playlist.current_track(state['songid'])
        if 'repeat' in changed:
            #             log.debug('************repeat***********: %s' %
            #                 bool(int(state['repeat'])))
            if self.repeat != bool(int(state['repeat'])):
                self.repeat = bool(int(state['repeat']))
                if not self.shuffle:
                    self.upnp_eventAV(
                        'REPEAT_ALL' if self.repeat else 'NORMAL',
                        'currentplayMode')
                else:
                    self.upnp_eventAV('REPEAT_ALL SHUFFLE' if self.repeat
                                      else 'NORMAL SHUFFLE', 'currentplaymode')
                self.oh_eventPLAYLIST(self.repeat, 'repeat')
        if 'random' in changed:
            log.debug('************shuffle***********: %s' %
                      bool(int(state['random'])))
            if self.shuffle != bool(int(state['random'])):
                self.shuffle = bool(int(state['random']))
                if not self.repeat:
                    self.upnp_eventAV(
                        'NORMAL SHUFFLE' if self.shuffle else 'NORMAL',
                        'currentplaymode')
                else:
                    self.upnp_eventAV(
                        'REPEAT_ALL SHUFFLE' if self.shuffle
                        else 'NORMAL SHUFFLE', 'currentplaymode')
                self.oh_eventPLAYLIST(self.shuffle, 'shuffle')
        if 'elapsed' in changed:
            if self.timer is not None:
                self.timer.set(float(state['elapsed']))
        if 'playlist' in changed:
            self.token = int(state['playlist'])
#             self.playlist.plsversion = state['playlist']
        if 'playlistdata' in changed:
            self.playlist.update(state['playlistdata'])
        if 'bitrate' in changed:
            self.detailscount += 1
            self.bitrate = int(state['bitrate'])
            self.oh_eventINFO(self.bitrate, 'bitrate')
        if 'audio' in changed:
            try:
                sr = int(state['audio'].split(':')[0])
                self.samplerate = sr
                self.oh_eventINFO(sr, 'samplerate')
            except:
                log.critical('Bad Samplerate: %s' %
                             state['audio'].split(':')[0])
            try:
                bd = int(state['audio'].split(':')[1])
                self.bitdepth = bd
                self.oh_eventINFO(bd, 'bitdepth')
            except:
                log.critical('Bad Bitdepth: %s' % state['audio'].split(':')[1])

    def update_state(self):
        #  log.err('Update State: %s' % self.mpd.status['state'])
        self.set_state(self.status['state'])

    def update_mimetypes(self):
        self.set_mimetypes(self.mimetypes)

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

    def getMetadata(self):
        return self.call('playlistid', self.status['songid'])

    def getMimeTypes(self):
        return self.call('decoders')

    def get_state(self):
        return self._state

    def get_rate(self):
        return self._rate

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

    def get_sticker(self, url, dic={}):

        def got_sticker(stklist, dic):
            if not isinstance(stklist, list):
                stklist = [stklist]
            for sticker in stklist:
                try:
                    dic.update(
                        {sticker['sticker'].split('=')[0],
                         sticker['sticker'].split('=')[1]})
                except:
                    continue
            return dic

        d = self.call('sticker', ' '.join(('list song', url.join('"' * 2))))
        d.addBoth(got_sticker, dic)
        return d

    def get_relcount(self):
        return 2147483647

    def get_abscount(self):
        return 2147483647

    def get_abstime(self):
        return '00:00:00'

    def get_reltime(self, fmt='UPNP'):
        if self.timer is not None:
            if fmt == 'UPNP':
                t = mpdtime_to_upnptime(self.timer.get())
            elif fmt == 'seconds':
                t = int(self.timer.get())
            else:
                # msec
                t = self.timer.get()
        else:
            if fmt == 'UPNP':
                t = self.reltime
            else:
                t = self.seconds
        return t

    def get_volume(self):

        def noVolume(err):
            if self._muted:
                return 0
            else:
                return self._volume

        def convert_volume(vol):
            self._volume = int(float(vol) * 100)
            return self._volume

        d = self.mediaplayer.get("Volume",
                                 interf='org.mpris.MediaPlayer2.Player')
        d.addCallbacks(convert_volume, noVolume)
        return d

    def get_transport_actions(self):
        return {','.join(self.transport_actions)}

    def set_mimetypes(self, mtlist):
        if self._mtlist != mtlist:
            self._mtlist = mtlist
            self.mtlist = 'http-get:*:' + ''\
                .join([':*,http-get:*:'.join(mtlist)]) + ':*'
            self.upnp_eventCM(self.mtlist, 'sinkprotocolinfo')
            self.oh_eventPLAYLIST(self.mtlist, 'protocolinfo')

    def set_metadata(self, metadata):
        if metadata != self.metadata:
            self.metadata.update(metadata)
            if 'duration' in metadata.keys():
                self._track_duration = metadata['duration']
            if 'url' in metadata.keys():
                self._track_URI = metadata['url']
            if 'file' in metadata.keys():
                self._track_URI = metadata['file']

    def set_reltime(self, t):
        self.seconds = int(float(t))
        self.reltime = mpdtime_to_upnptime(t)
#         log.err('seconds: %s' % t)
        self.timer = None

    def set_state(self, state):
        log.debug("SET NEW STATE : %s " % state)
        if state == self._state:
            return
        self._state = state
        if state == 'pause':
            #             print(self.transport_actions)
            self.transport_actions = ['PLAY', 'STOP']
#                 self.transport_actions.remove('PAUSE')
#                 self.transport_actions.append('PLAY')
            if self.timer is not None:
                self.timer.stop()
                d = self.call('status')
                d.addCallback(lambda st: st['elapsed'])
                d.addCallbacks(
                    self.set_reltime,
                    lambda ignored: self.set_reltime(self.timer.get()))
            self.upnp_state = 'PAUSED_PLAYBACK'
            self.oh_state = 'Paused'
        elif state == 'play':
            self.transport_actions = ['STOP', 'PAUSE', 'SEEK']
            self.changed_state({'volume': self.status['volume']})
            self.timer = Timer()
            self.timer.set(self.seconds)
            d = self.call('status')
            d.addCallbacks(lambda st: st['elapsed'])
            d.addCallbacks(lambda t: self.timer.set(float(t)),
                           lambda ignored: self.timer.set(0.000))
            self.upnp_state = 'PLAYING'
            self.oh_state = 'Playing'
        elif state == 'stop':
            self.transport_actions = ['PLAY']
            self.set_reltime(0)
            self.upnp_state = 'STOPPED'
            self.oh_state = 'Stopped'
        elif state == 'pending':
            self.upnp_state = 'TRANSITIONNING'
            self.oh_state = 'Buffering'
        else:
            return
        self.upnp_eventAV(self.upnp_state, 'transportstate')
        self.oh_eventPLAYLIST(self.oh_state, 'transportstate')

    def set_songid(self, songid):
        self.songid = songid['Id']
        return self.songid

    def set_position(self, newpos, fmt='UPNP'):
        def transition(obj):
            current_state = self._state
            self.set_state('pending')
            reactor.callLater(0.5,  # @UndefinedVariable
                              self.set_state,
                              current_state)
        if fmt == 'UPNP':
            pos = upnptime_to_mpdtime(newpos)
        else:
            pos = newpos
        log.debug('seek to %s' % pos)
        d = self.call('seekcur', pos)
        d.addCallback(transition)
        return d

    def set_position_relative(self, delta, fmt='UPNP'):
        newpos = int(self.get_reltime('Seconds')) + int(delta)
        self.set_position(newpos, fmt)

    def set_track_URI(self, uri, md=''):
        log.debug("set track uri : %s " % uri)
        try:
            log.debug("current uri : %s " % self._track_URI)
        except:
            pass
        if uri != self._track_URI:
            self._track_URI = uri
            self.metadata_str = md
            self.set_metadata(didl_decode(md.encode('utf-8')))
            d = self.call('addid', uri)
            d.addCallback(self.set_songid)
            d.addCallback(self.play)

    def playing(self, *ret):
        log.debug('playing...')
        self.set_state('play')

    def playindex(self, index):
        return self.play(songid=self.playlist[int(index)])

    def playpause(self):
        if self._state == 'pause':
            return self.play()
        else:
            return self.pause()

    def insert_metadata(self, md):
        dic = didl_decode(md)
#             log.err(dic)
        for i, tag in enumerate(dic.keys()):
            if tag.lower() in ('class', 'restricted', 'id', 'duration',
                               'parentid', 'protocolinfo', 'url',
                               'ownerudn'):
                continue
            if not isinstance(dic[tag], str):
                continue
            reactor.callLater(  # @UndefinedVariable
                float(i) / 2,
                self.call,
                ' '.join(('sticker',
                          'set song',
                          dic['url'].join('"' * 2),
                          tag,
                          '"' + dic[tag] + '"')))

    def delete(self, songid):
        self.call('deleteid', str(songid))

    def clear(self):
        self.call('clear')

    def volUp(self):
        if self._volume == 0:
            vol = self.r_get_volume()
            try:
                newvol = vol + 5
            except:
                newvol = self._volume + 5
            return self.r_set_volume(newvol, 'Master')
        else:
            if self._volume > 95:
                return
            newvol = self._volume + 5
            return self.r_set_volume(newvol, 'Master')

    def volDown(self):
        if self._volume > 5:
            newvol = self._volume - 5
            return self.r_set_volume(newvol, 'Master')
        else:
            newvol = self._volume
            self._volume = 0
            return self.r_set_volume(newvol, '0')

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
        return self.clear()

    def r_delete_id(self, value):
        return self.delete(value)

    def r_get_current_transport_actions(self, instanceID):
        return self.get_transport_actions()

    def r_get_media_info(self, instanceID):
        return (str(len(self.playlist)), self.get_track_duration(),
                self.get_track_URI(), self.get_track_md(), '', '', 'UNKNOWN',
                'UNKNOWN', 'UNKNOWN',)

    def r_get_media_info_ext(self, instanceID):
        return (str(len(self.playlist)), 'TRACK_AWARE',
                self.get_track_duration(), self.get_track_URI(),
                self.get_track_md(), '', '', 'UNKNOWN', 'UNKNOWN',
                'UNKNOWN',)

    def r_get_position_info(self, instanceID):
        return (self.player.get_track(), self.get_track_duration(),
                self.get_track_md(), self.player.get_track_URI(),
                self.player.get_reltime(), self.player.get_abstime(),
                self.player.get_relcount(), self.player.get_abscount(),)

    def r_get_transport_info(self, instanceID):
        return (self.get_state(), 'OK', self.get_rate(),)

    def r_id(self):
        return self.songid

    def r_id_array(self):
        return (self.token, self.idArray,)

    def r_id_array_changed(self, token):
        if token != self.token:
            return 1
        return 0

    def r_insert(self, afterid, url, metadata, checked=False):
        log.debug('Insert :%s  --  %s  --  %s' % (afterid, url, metadata))

        def inserted(res, md):
            log.debug(res)
            return res['Id']

        if 'youtube' in url and not checked:
            # eclipse workaround !!!
            y = os.environ
            y.update({'PYTHONPATH': '/usr/bin/python'})
            # /eclipse workaround
            d = utils.getProcessOutput(
                '/usr/bin/youtube-dl',
                ['-g', '-f', 'bestaudio', url],
                env=y,
                reactor=reactor)
            d.addCallback(
                lambda u: self.insert(
                    u.split('\n')[0], afterid, metadata, True))
            return d
        if len(self.playlist.tracks) == 0:
            d = self.call('addid', url)
        elif int(afterid) == 0:
            d = self.call('addid', url + ' 0')
        else:
            log.critical('crash ? %s' % self.playlist.tracks)
            log.critical('here ? %s' %
                         str(self.playlist.tracks.index(int(afterid)) + 1))
            d = self.call(
                'addid',
                ' '.join(
                    (url.encode('utf-8'),
                     str(self.playlist.tracks.index(int(afterid)) + 1))))
        d.addCallback(inserted, metadata)
        return d

    def r_next(self, instanceID=0):
        if self._state not in ('play', 'pause'):
            if self.songid == 0:
                self.r_play(1)
            else:
                self.r_play()
        else:
            self.call('next')

    def r_play(self, instanceID=0, speed=1, songid=None,
               ignored=None):

        log.debug('entering play...')

        def success(result):
            return None
        if self.cancelplay:
            self.cancelplay = False
        else:
            if songid is not None:
                #                 log.err(songid)
                d = self.call('playid', str(songid))
            else:
                if self._state == 'pause':
                    d = self.call('pause', '0')
                else:
                    d = self.call('playid', self.songid)
            d.addCallback(self.playing)

    def r_pause(self, instanceID=0):
        print('pause')

        def paused(ret):
            if self._state == 'play':
                self.set_state('pause')
        d = self.call('pause', '1')
        d.addCallback(paused)
        return d

    def r_previous(self, instanceID=0):
        self.call('previous')

    def r_protocol_info(self):
        return self.protocolinfo

    def r_read(self, value):
        log.debug('read')
        d = self.playlist.get_track(value)
        return (d,)

    def r_read_list(self, items):
        log.debug('readlist')
        d = self.playlist.get_tracks(
            [int(track) for track in items.split()])
        return d

    def r_repeat(self):
        return self.repeat

    def r_record(self, instanceID):
        raise NotImplementedError()

    def r_seek(self, instanceID, unit, pos):
        log.debug('seek: %s %s' % (unit, pos))
        self.set_position(pos)

    def r_seek_id(self, value):
        log.debug('SeekId')
        return self.r_play(songid=value)

    def r_seek_index(self, value):
        log.debug('Seekindex')
        return self.playindex(value)

    def r_seek_second_absolute(self, value):
        return self.set_position(value, 'SECONDS')

    def r_seek_second_relative(self, value):
        return self.set_position_relative(value, 'SECONDS')

    def r_set_repeat(self, repeat):
        self.call('repeat', str(int(repeat)))
        self.changed_state({'repeat': str(int(repeat))})

    def r_set_shuffle(self, shuffle):
        self.call('random', str(int(shuffle)))
        self.changed_state({'random': str(int(shuffle))})

    def r_set_avtransport_uri(self, instanceID, uri, uri_metadata):
        self.set_track_URI(uri, uri_metadata)

    def r_shuffle(self):
        return self.shuffle

    def r_stop(self, instanceID=0):
        def stopped(ret):
            self.set_state('stop')
        if self._state != 'STOPPED':
            d = self.call('stop')
            self.reltime = '00:00:00'
            d.addCallback(stopped)

    def r_tracks_max(self):
        return self.tracksmax

    def r_transport_state(self, instanceID=0):
        if self.parent.type == 'Source':
            return self.oh_state
        return self.upnp_state

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
        return self._volume

    def r_set_volume(self, volume, channel=0):
        volume = str(volume)
        d = self.call('setvol', volume)
        d.addErrback(
            log.critical,
            'Set Volume Error : %s - %d' % (channel, int(volume)))
        reactor.callLater(0.1,  # @UndefinedVariable
                          self.changed_state,
                          {'volume': str(volume)})

    def r_volume_inc(self):
        return self.volUp()

    def r_volume_dec(self):
        return self.volDown()

    def r_volume_limit(self):
        return self.max_volume

    def r_balance(self):
        return self.balance

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
                self.r_set_volume('0')
            else:
                self.r_set_volume(self.old_vol)

    def r_characteristics(self):
        return self.max_volume, self.volumeunity, self.max_volume,\
            self.volumemillidbperstep, self.balancemax, self.fademax

    '''
    OpenHome Time
    '''

    def r_time(self):
        return (self.trackcount, self.ohduration, self.get_reltime('seconds'))

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


def get_Mpd(addr='127.0.0.1', port=6600, cover_dir='/var/lib/mpd/',
            net_type='lan'):
    f = Mpd_factory(cover_dir=cover_dir, net_type=net_type)
    if addr.startswith('/') or addr.startswith('~'):
        reactor.connectUNIX(addr, f)  # @UndefinedVariable
#         from twisted.internet.endpoints import UNIXClientEndpoint
#         edp = UNIXClientEndpoint(reactor, addr)
#         edp.connect(f)
    else:
        reactor.connectTCP(addr, port, f)  # @UndefinedVariable
#         from twisted.internet.endpoints import TCP4ClientEndpoint
#         edp = TCP4ClientEndpoint(reactor, addr, port)
#         edp.connect(f)

    return None, f

if __name__ == '__main__':
    #     from twisted.internet.task import deferLater

    def print_fct(result):
        print('func result: %s' % result)
        if isinstance(result, list):
            print(len(result))
            for r in result:
                if 'Id' not in r:
                    print('!!!!!!!!!!!!! %s !!!!!!!!!!!' % r)
                print(r)
#                 print(r)
        else:
            print('single result: %s' % result)

    def print_event(evt=''):
        print('intercepted: %s' % evt)
    mpd = Mpd_factory()
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
#             d = mpd.call('plchanges', '0')
#             d.addCallback(print_fct)
#             d = mpd.call('playlistinfo')
#             d.addCallback(print_fct)
#             d = mpd.call(
#                 'addid http://192.168.0.10:8200/MediaItems/2108.flac')
#             d.addCallback(print_fct)
#             d = mpd.call(
#                 'sticker',
#                 'set song "http://192.168.0.10:8200/MediaItems/2108.flac"
#                     toto tata')
#             d.addCallback(print_fct)
#             d = mpd.call(
#                 'sticker',
#                 'list song "http://192.168.0.10:8200/MediaItems/2108.flac"')
#             d.addCallback(print_fct)
#             d = mpd.call('seekcur', '25')
#             d.addCallback(print_fct)
#             d = mpd.call('playlistid')
#             d.addCallback(print_fct)
#             d = mpd.call('playlistinfo', '227' )
#             d.addCallback(print_fct)
        else:
            reactor.callLater(1, test)  # @UndefinedVariable
    reactor.callWhenRunning(test)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
