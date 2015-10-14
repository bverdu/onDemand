# -*- coding: utf-8 -*-
'''
Created on 5 sept. 2014

@author: Bertrand Verdu
'''
from fractions import Fraction
import os
import signal
import dbus

import psutil
from twisted.application.service import Service
from twisted.internet import reactor, \
    protocol, \
    defer, \
    task, \
    threads, \
    utils
from twisted.python import log

from mpyris.mediaplayer import MediaPlayer
from onDemand.utils import mpristime_to_upnptime, \
    upnptime_to_mpristime, \
    dbus_func_failed, \
    mpris_decode
from upnpy.utils import didl_decode, didl_encode, id_array
import xml.etree.cElementTree as et


class Mprisclient(Service):
    '''
    Manage player through dbus mpris interface
    '''
    name = "MprisPlayer"
    launching = True
    launched = False
    connected = False
    repeat = False
    shuffle = False
    has_tracklist = False
    playlist = []
    _playlist = []
    oh_playlist = []
    songid = 0
    maxsongid = 0
    numid = {}
#     badlist =[]
    idArray = ''
    tracksmax = 10000
    max_volume = 100
    _state = "Pending"
    upnp_state = "TRANSITIONING"
    oh_state = 'Buffering'
    _duration = 0
    reltime = '0:00:00'
    seconds = 0
    _track_URI = ''
    _managed = False
    _errors = 0
    stopping = False
    _volume = 100
    notify = False
    rate = '1'
    _rate = ""
    _mtlist = ''
    mtlist = ''
    _muted = False
    timer = False
    metadata = {}
    _metadata = {}
    metadata_str = 'NOT_IMPLEMENTED'
    playfunc = None
    mediaplayer = None

    def __init__(self, program='', args=None, **kwargs):
        '''
        Constructor
        '''
        self.playercmd_args = args
        self.player_path = program
        self.player_args = [program]
        self.player = program.split("/")[-1]

    def startService(self):
        '''
        Check and launch player program
        '''
#         print(self.playercmd_args, self.player_path)
        self.launch_player()

    def launch_player(self, test=False):
        if self.playercmd_args is not None:
            self.player_args = [self.player_path]\
                + self.playercmd_args.split()
        for proc in psutil.process_iter():
            if proc.name() == self.player:
                log.msg('Player process found', loglevel=logging.DEBUG)
                self._managed = False
                self.extpid = proc.pid
                self.juststarted = False
                reactor.callWhenRunning(self.connect)  # @UndefinedVariable
                if test:
                    if self._errors > 5:
                        try:
                            self.protocol.shutdown()
                        except:
                            proc.kill()
                        return False
                    else:
                        self._errors += 1
                        return True
                return None
        if test:
            return False
        self._managed = True
        try:
            reactor.spawnProcess(  # @UndefinedVariable
                PlayerProcess(self),
                self.player_path,
                self.player_args,
                env=os.environ)
        except:
            log.err("Program unknown : %s" % self.player_args)

    def connect(self, first=True):
        '''
        Try to get dbus connection with player
        '''
        def gotPlayer(name):
            self.connected = True
            self.launched = True
            log.msg("got dbus connection with player")
            log.msg("player = %s" % name.encode('utf-8'), loglevel=logging.DEBUG)
            self._errors = 0
            self.getStatus()

        def noPlayer(err):
            self.connected = False
            if self._errors > 5:
                self.launch_player(True)
                log.msg("maximum number of errors reached, \
                                killing player process")
                return
            self._errors += 1
            log.msg("get dbus client failed: %s" % err.getErrorMessage())
        if self.connected:
            return defer.succeed(None)
        if self.mediaplayer is None:
            self.mediaplayer = MediaPlayer(self.player)
        d = self.mediaplayer.connect()
        d.addCallbacks(gotPlayer, noPlayer)
        return d

    def reconnect(self):
        if not self.connected:
            if not self.launched:
                test = self.launch_player(True)
                if test is False:
                    reactor.callLater(10,  # @UndefinedVariable
                                      self.reconnect)

    def checkPid(self):
        print('.')
        try:
            if self.extpid.poll() is None:
                reactor.callLater(3, self.checkPid)  # @UndefinedVariable
            else:
                #                 log.msg("ext process stopped")
                self.extpid = None
                self.launched = False
                self.set_state('Stopped')
                self.connectionLost('Player process died')
        except:
            try:
                p = psutil.Process(self.extpid)
                del(p)
                reactor.callLater(3, self.checkPid)  # @UndefinedVariable
            except:
                self.extpid = None
                self.launched = False
                self.set_state('Stopped')
                self.connectionLost('Player process died')
#                 log.msg("ext process stopped: %s" % e)

    def endprocess(self):
        try:
            self._self.protocol.shutdown()
        except AttributeError:
            try:
                os.kill(self.extpid, signal.SIGINT)
            except Exception, e:
                log.err("endprocess failure : %s" % e.message)
            self.stopping = False

    def disconnected(self, obj=None, reason=''):
        log.msg('dbus disconnected, reason=%s' % reason, loglevel=logging.DEBUG)
        self.connected = False
        self.set_state('Stopped')

    def connectionLost(self, reason):
        self.disconnected(reason=reason)
        self.set_state('Ended')
        self.launched = False
        self.getStatus = self.getStatusFirst
        reactor.callLater(10, self.reconnect)  # @UndefinedVariable
        if self.stopping:
            try:
                self._down.cancel()
            except:
                pass
            self.stopping = False

    def getStatus(self):
        return self.getStatusFirst()

    def getStatus_(self):
        log.err('status')
        if self.launched:
            d = self.mediaplayer.get(
                "PlaybackStatus",
                interf='org.mpris.MediaPlayer2.Player')
            d.addCallbacks(self.set_state,
                           dbus_func_failed,
                           errbackArgs=('PlaybackStatus',))
            reactor.callLater(3, self.checkPid)  # @UndefinedVariable
            dd = self.mediaplayer.get("SupportedMimeTypes")
            dd.addCallbacks(self.set_mimetypes, dbus_func_failed,
                            errbackArgs=('SupportedMimeTypes',))
            ddd = self.mediaplayer.get(
                "Volume",
                interf='org.mpris.MediaPlayer2.Player')
            ddd.addCallbacks(
                lambda v: self.changed_state(
                    'org.mpris.MediaPlayer2.Player',
                    {'Volume': v},
                    0),
                dbus_func_failed,
                errbackArgs=('Get Volume',))
            if self.mediaplayer.tracklist:
                self.has_tracklist = True
                log.err('Tracklist !!!')
                self.update_playlist()
            self.launching = False
            if not self.notify:
                reactor.callLater(  # @UndefinedVariable
                    3,
                    self.getStatus,
                    False)
        else:
            if self.launch_player(True):
                self.getStatus = self.getStatusFirst
                return self.getStatus()

    def getStatusFirst(self):
        log.err('statusFirst')
        self.notify = False
        try:
            self.mediaplayer.register_signal('PropertiesChanged',
                                             self.changed_state)
        except:
            log.msg("dbus register signal not supported, polling...",
                    loglevel=logging.DEBUG)
        else:
            self.notify = True
            self.mediaplayer.register_signal('NameLost',
                                             self.disconnected,
                                             interf='org.freedesktop.DBus')
            log.msg("notify = OK", loglevel=logging.DEBUG)
        self.getStatus = self.getStatus_
        task.deferLater(reactor, 1, self.getStatus)

    def getMetadata(self):
        if self.launched:
            d = self.mediaplayer.get("Metadata",
                                     interf='org.mpris.MediaPlayer2.Player')
            d.addCallbacks(self.update_metadata,
                           dbus_func_failed,
                           errbackArgs=("Metadata",))
            return self.metadata
        else:
            if self.launch_player(True):
                return self.getMetadata()

    def changed_state(self, dbus_interface, msg, lst, pending=False):
        log.msg('remote client %s changed state = %s %s' %
                (dbus_interface, msg, lst), loglevel=logging.DEBUG)
        if 'PlaybackStatus' in msg.keys():
            if len(msg['PlaybackStatus']) > 1:
                self.set_state(msg['PlaybackStatus'])
        if 'Rate' in msg.keys():
            self._rate = msg['Rate']
            self.rate = str(
                Fraction(float(self._rate)).
                limit_denominator(1).
                numerator)\
                + "/"\
                + str(Fraction(float(self._rate)).
                      limit_denominator(1).denominator)
        if "Volume" in msg.keys():
            log.msg('volume changed', loglevel=logging.DEBUG)
            vol = int(float(msg["Volume"])*100)
            if vol != self._volume:
                if vol != 0:
                    self._volume = int(float(msg["Volume"])*100)
                    self._muted = False
                else:
                    self._muted = True
                log.msg('send volume', loglevel=logging.DEBUG)
                self.upnp_eventRCS(self._volume, 'Volume')
                self.oh_eventVOLUME(self._volume, 'volume')
        if 'Metadata' in msg.keys():
            self.update_metadata(msg['Metadata'])
        if 'TrackList' in dbus_interface:
            log.err('playlist update')
            self.update_playlist()

    def guess_play_func(self):
        # omxplayer fix
        def playfuncplay(result):
            self.playfunc = 'Play'
            return result

        def playfuncpause(err):
            self.playfunc = 'Pause'
            raise Exception('No Play')

        d = self.mediaplayer.call('Play')
        d.addCallbacks(playfuncplay, playfuncpause)
        return d

    def update_playlist(self):
        def updated(ignored):
            self.oh_eventPLAYLIST(id_array(self.playlist), 'idarray')
        if self.has_tracklist:
            def got_tracks(tracks):
                if self._playlist != tracks:
                    self._playlist = tracks
                    log.err(self._playlist)
                    self.playlist = []
                    for track in self._playlist:
                        if str(track) in self.numid:
                            songid = self.numid[str(track)]
                        else:
                            self.maxsongid += 1
                            songid = self.maxsongid
                        self.numid.update({songid: str(track)})
                        self.numid.update({str(track): songid})
                        self.playlist.append(songid)
#                 if len(self.badlist) > 0:
#                     self.playlist = self.playlist + self.badlist
            d = self.mediaplayer.get(
                'Tracks', interf='org.mpris.MediaPlayer2.TrackList')
            d.addCallback(got_tracks)
        else:
            d = defer.succeed(None)
        d.addCallback(updated)

    def update_metadata(self, metadata):

        if metadata == self._metadata:
            return
        self._metadata = metadata
        metadata = mpris_decode(metadata)
        songid = None
        if self.has_tracklist:
            if 'mpris:trackid' in metadata:
                try:
                    if self.songid != self.numid[
                            str(metadata['mpris:trackid'])]:
                        songid = self.numid[
                            str(metadata['mpris:trackid'])]
                except KeyError:
                    if 'url' in metadata:
                        self.maxsongid += 1
                        self.numid.update(
                            {self.maxsongid: str(metadata['mpris:trackid'])})
                        self.numid.update(
                            {str(metadata['mpris:trackid']): self.maxsongid})
                        self.playlist.append(self.maxsongid)
#                         if len(self.badlist) > 0:
#                             songid = self.badlist.pop(0)
#                             self.numid.update(
#                                 {songid: str(metadata['mpris:trackid'])})
#                             self.numid.update(
#                                 {str(metadata['mpris:trackid']): songid})
#                         else:
#                             self.insert(
#                                 metadata['url'], self.maxsongid, metadata)
            elif 'songid' in metadata:
                if self.songid != int(metadata['songid']):
                    songid = int(metadata['songid'])
        else:
            if 'songid' in metadata:
                if self.songid != int(metadata['songid']):
                    songid = int(metadata['songid'])
            else:
                if 'url' in metadata:
                    for track in self._playlist:
                        if track[1] == metadata['url']:
                            songid = track[0]
                            metadata.update(track[2])
                            break
                    else:
                        songid = self.maxsongid + 1
                        self.insert(metadata['url'], self.maxsongid, metadata)
        if songid:
            self.songid = songid
            self.metadata = {}
            self.upnp_eventAV(int(self.songid), 'CurrentTrack')
            self.oh_eventPLAYLIST(int(self.songid), 'id')
            self.oh_eventTIME(1, 'trackcount')
        if 'duration' in metadata:
            if self._duration != metadata['duration']:
                duration = int(metadata['duration'])
                log.err('duration: %d' % duration)
                if duration < 1:
                    self._track_duration = "0:00:00"
                    self._duration = 0
                else:
                    self._duration = duration
                    self._track_duration = mpristime_to_upnptime(duration)
                log.msg('track length: %s'
                        % self._track_duration, loglevel=logging.DEBUG)
                self.upnp_eventAV(self._track_duration,
                                  'CurrentTrackDuration')
                self.oh_eventINFO(int(self._duration//1000000), 'duration')
                self.oh_eventTIME(int(self._duration//1000000), 'duration')
        if 'url' in metadata:
            if self._track_URI != metadata['url']:
                self._track_URI = metadata['url']
                self.upnp_eventAV(self._track_URI, 'AVTransportURI')
                self.oh_eventINFO(self._track_URI, 'uri')
                self.upnp_eventAV(self._track_URI, 'CurrentTrackURI')
        if 'mpris:artUrl' in metadata:
            url = self.parent.register_art_url(metadata['mpris:artUrl'])
            metadata['albumArtURI'] = url
        self.metadata.update(metadata)
        self.metadata_str = didl_encode(self.metadata)
        self.oh_eventINFO(self.metadata_str, 'metadata')
        self.upnp_eventAV(self.metadata_str, 'AVTransportURIMetaData')

    def set_metadata(self, metadata):
        if metadata != self.metadata:
            self.metadata.update(metadata)
            if 'duration' in metadata.keys():
                self._track_duration = metadata['duration']
            if 'url' in metadata.keys():
                self._track_URI = metadata['url']

    def set_state(self, state):
        log.msg("SET NEW STATE : %s " % state, loglevel=logging.DEBUG)
        if state in ['Stop', 'Play', 'Pause']:
            return
        if state == self._state:
            return
        log.msg('send new state: %s' % state, loglevel=logging.DEBUG)
        if state == 'Ended':
            self.has_tracklist = False
            self.idArray = ''
            self.oh_eventPLAYLIST(self.idArray, 'idarray')
            return
        self._state = state
        self.oh_state = state
        if state == "Paused":
            self.upnp_state = "PAUSED_PLAYBACK"
        if state == 'Pending':
            self.upnp_state = "TRANSITIONNING"
            self.oh_state = 'Buffering'
        self.upnp_eventAV(self.upnp_state, 'TransportState')
        self.oh_eventPLAYLIST(self.oh_state, 'transportstate')
        if self._state == "Stopped":
            self.timer = False
            self.seconds = 0
            self.reltime = '0.00.00.000'
            if self.launched:
                if (not self.stopping) and self._managed:
                    self._down = reactor.callLater(  # @UndefinedVariable
                        5,
                        self.endprocess)
                    self.stopping = True
                    return defer.succeed(None)
        if self._state == "Playing":
            if self.stopping:
                self._down.cancel()
                self.stopping = False
            self.timer = True
#             self.mediaplayer.set('Fullscreen', True)
#             reactor.callLater(1, self.getMetadata)  # @UndefinedVariable
            if self.playfunc is None:
                d = self.guess_play_func()
                return d

    def set_mimetypes(self, mtlist):
        #         log.msg("mtlist: % s" % mtlist)
        if self._mtlist != mtlist:
            self._mtlist = mtlist
            self.mtlist = 'http-get:*:'+''.join(
                [':*,http-get:*:'.join(mtlist)])+':*'
            self.upnp_eventCM(self.mtlist, 'SinkProtocolInfo')
            self.oh_eventPLAYLIST(self.mtlist, 'protocolinfo')

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
        return self.get_tracks([track])

    def get_tracks(self, tracks):
        log.err('ooooOOOooo')

        def generate_tracklist(tracks):
            if not isinstance(tracks, list):
                tracks = [tracks]
#             if len(self.badlist) > 0:
#                 for tr in self.badlist:
#                     tracks.append(self.numid[tr]['metadata'])
            tl = et.Element('TrackList')
            for track in tracks:
                log.err('track: %s' % track)
                track = mpris_decode(track)
                en = et.Element('Entry')
                i = et.Element('Id')
                try:
                    i.text = str(self.numid[track['mpris:trackid']])
                except:
                    i.text = str(track['songid'])
                en.append(i)
                uri = et.Element('Uri')
                uri.text = track['url'].decode('utf-8')
                en.append(uri)
                md = et.Element('Metadata')
                md.text = didl_encode(track)
                en.append(md)
                tl.append(en)
            return et.tostring(tl)
        if self.has_tracklist:
            tl = []
            for track in tracks:
                tl.append(dbus.ObjectPath(self.numid[int(track)]))
            if len(tl) > 0:
                d = self.mediaplayer.call(
                    'GetTracksMetadata',
                    tl,
                    interf='org.mpris.MediaPlayer2.TrackList')
            else:
                d = defer.succeed([])
        else:
            tl = []
            for track in tracks:
                ind = self.playlist.index(track)
                tl.append(self._playlist[ind][2])
            d = defer.succeed(tl)
        d.addCallback(generate_tracklist)
        return d

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

#     def get_track(self):
#         if self._state == 'STOPPED':
#             track = 0
#         else:
#             track = 1
#         return track

    def get_relcount(self):
        return 2147483647

    def get_abscount(self):
        return 2147483647

    def get_abstime(self):
            return '00:00:00'

    def get_reltime(self, fmt='UPNP'):
        def setCounter(counter):
            if self._duration != 0:
                if self._duration - counter < 2000000:
                    if not self.has_tracklist:
                        self._duration = 0
                        reactor.callLater(2, self.next)  # @UndefinedVariable
            self.seconds = counter/1000000.000
            return counter

        def setTime(time):
            self.reltime = time

        def noTime(err):
            return "00:00:00"

        if self.launched:
            d = self.mediaplayer.get("Position",
                                     interf='org.mpris.MediaPlayer2.Player')
            d.addCallbacks(setCounter, noTime)
            d.addCallback(mpristime_to_upnptime,
                          (self._state, self.reltime,))
            d.addBoth(setTime)
#         else:
#             if self.launch_player(True):
#                 log.msg('Player is already launched,
#                     status = %s , try again' % self._state,
#                     loglevel=logging.DEBUG)
#                 reactor.callLater(1, self.get_reltime)#@UndefinedVariable
        if fmt == 'UPNP':
            return self.reltime
        else:
            if self._state == 'Playing':
                return self.seconds + 2
            else:
                return self.seconds

    def get_volume(self):
        if self.launched:
            def noVolume(err):
                if self._muted:
                    return 0
                else:
                    return self._volume

            def convert_volume(vol):
                self._volume = int(float(vol)*100)
                log.msg("volume= %d" % self._volume, loglevel=logging.DEBUG)
                return self._volume

            d = self.mediaplayer.get("Volume",
                                     interf='org.mpris.MediaPlayer2.Player')
            d.addCallbacks(convert_volume, noVolume)
            return d
        else:
            if self.launch_player(True):
                return self.get_volume()

    def set_volume(self, channel, volume):
        if self.launched:
            if int(volume) != 0:
                d = self.mediaplayer.set(
                    "Volume",
                    float(int(volume)/100.00),
                    interf='org.mpris.MediaPlayer2.Player')
            else:
                if self._muted:
                    d = self.mediaplayer.set(
                        "Volume",
                        float(self._volume/100.00),
                        interf='org.mpris.MediaPlayer2.Player')
                else:
                    d = self.mediaplayer.set(
                        "Volume",
                        0.00,
                        interf='org.mpris.MediaPlayer2.Player')
            d.addErrback(
                dbus_func_failed,
                'Set Volume : %s - %d' % (channel, int(volume)))
            self._event = True
            reactor.callLater(0.1, self.changed_state,  # @UndefinedVariable
                              *('org.mpris.MediaPlayer2.Player',
                                {'Volume': float(int(volume)/100.00)},
                                0,
                                True,))
        else:
            if self.launch_player(True):
                return self.set_volume(channel, volume)

    def set_track_URI(self, uri, md=''):
        log.msg("set track uri : %s " % uri, loglevel=logging.DEBUG)
        try:
            log.msg("current uri : %s " % self._track_URI, loglevel=logging.DEBUG)
        except:
            pass
        if uri != self._track_URI:
            self._track_URI = uri
            self.metadata_str = md
            self.set_metadata(didl_decode(md.encode('utf8')))
            if self.launched:
                if self.stopping:
                    self._down.cancel()
                    self.stopping = False
                if self.playfunc != 'Pause':
                    # omxplayer fix
                    d = self.mediaplayer.call('OpenUri', uri)
                    d.addErrback(dbus_func_failed, ('OpenUri : %s' % uri,))
#                 else:
#                     self.play()
#             else:
#                 self.play()
#         else:
#             self.play()

    def set_position(self, newpos, fmt='UPNP'):
        if self.launched:
            def transition(obj):
                current_state = self._state
                self.set_state('Pending')
                reactor.callLater(  # @UndefinedVariable
                    0.5,
                    self.set_state,
                    current_state)
            if fmt == 'UPNP':
                newtime = upnptime_to_mpristime(newpos)
                offset = newtime - self.seconds
            else:
                offset = float(newpos) - self.seconds
            d = self.mediaplayer.call('Seek', offset)
            d.addCallbacks(transition, dbus_func_failed,
                           errbackArgs=('Seek %d' % offset,))
            return d
        else:
            if self.launch_player(True):
                return self.set_position(newpos)

    def play(self, ignored=None, songid=None):
        if self.launched:
            #  print('launched')
            if songid:
                if self.has_tracklist:
                    i = dbus.ObjectPath(self.numid[int(songid)])
                    self.mediaplayer.call(
                        'GoTo', i, interf='org.mpris.MediaPlayer2.TrackList')
                    i = dbus.ObjectPath(
                        self.numid[int(songid)])
                    self.mediaplayer.call(
                        'GoTo', i, interf='org.mpris.MediaPlayer2.TrackList')
                else:
                    self.songid = int(songid)
                    self._track_URI = str(self._playlist[
                        self.playlist.index(int(songid))][1])
#                     log.err(self._playlist[
#                         self.playlist.index(int(songid))][1])
                    d = self.mediaplayer.call('OpenUri', self._track_URI)
                    d.addErrback(
                        dbus_func_failed, ('OpenUri : %s' % self._track_URI,))
                    self.update_metadata(
                        self._playlist[self.playlist.index(int(songid))][2])
#                     return d
            if self.stopping:
                self._down.cancel()
                self.stopping = False
            if self.playfunc is None:
                d = self.guess_play_func()
                d.addErrback(self.play)
            else:
                if (self._state in ['Paused', 'Pending'])\
                        or (self.playfunc != 'Pause'):
                    d = self.mediaplayer.call(self.playfunc)
                elif self.playfunc == 'Pause':
                    # omxplayer fix, let it close properly
                    reactor.callLater(1, self.play)  # @UndefinedVariable
                    return
            d.addCallbacks(lambda ignored: self.set_state('Playing'),
                           dbus_func_failed,
                           errbackArgs=(self.playfunc,))
#             return d
        else:
            if songid:
                self._track_URI = self._playlist[
                    self.playlist.index(int(songid))][1]
            if self.launch_player(True):
                # reactor.callLater(2, self.play)#@UndefinedVariable
                return
            reactor.spawnProcess(  # @UndefinedVariable
                PlayerProcess(self),
                self.player_path,
                [arg for arg in (
                    self.player_args+[self._track_URI]
                    if self._track_URI != '' else self.player_args)],
                env=os.environ)
            self._managed = True

    def playpause(self):
        if self._state == 'Paused':
            return self.play()
        else:
            return self.pause()

    def pause(self):
        if self.launched:
            self.mediaplayer.call('Pause')
            d = self.mediaplayer.call('Pause')
            d.addCallbacks(lambda ignored: self.set_state('Paused'),
                           dbus_func_failed,
                           errbackArgs=('Pause',))
        else:
            if self.launch_player(True):
                return self.pause()

    def stop(self):
        if self._state != 'Stopped':
            self.mediaplayer.call('Stop')
            self.reltime = '00:00:00'
#             d = self.mediaplayer.call('Stop')
#             d.addCallbacks(lambda ignored: self.set_state('Stopped'),
#                            dbus_func_failed,
#                            errbackArgs=('Stop',))

    def next(self):
        if self.has_tracklist:
            self.mediaplayer.call('Next')
        else:
            if len(self.playlist) > 0:
                if self.songid == self.playlist[-1]:
                    if self.repeat:
                        self.play(songid=self.playlist[0])
                else:
                    self.play(
                        songid=self.playlist[
                            self.playlist.index(self.songid) + 1])

    def previous(self):
        if self.has_tracklist:
            self.mediaplayer.call('Previous')
        else:
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
                newvol = self._volume + 5
            return self.set_volume('Master', newvol)
        else:
            if self._volume > 95:
                return
            newvol = self._volume + 5
            return self.set_volume('Master', newvol)

    def volDown(self):
        if self._volume > 5:
            newvol = self._volume - 5
            return self.set_volume('Master', newvol)
        else:
            self._volume = 0
            return self.set_volume('Master', 0)

    def insert(self, url, afterid, metadata, checked=False):

        #         def get_newid(ignored):
        #             d = self.mediaplayer.get(
        #                 'Tracks', interf='org.mpris.MediaPlayer2.TrackList')
        #             d.addCallback(got_id)
        #             return d
        #
        #         def got_id(newidlist):
        #             print(newidlist)
        #             newid = [
        #             item for item in newidlist if item not in self._playlist]
        #             try:
        #                 return newid[0]
        #             except:
        #                 print("gggg")
        #                 self.badlist.append(self.maxsongid+1)
        #                 return {'pos': self.maxsongid+1}
        #
        #         def inserted(res, md):
        #             self.maxsongid += 1
        #             if isinstance(res, dict):
        #                 meta = didl_decode(md.encode('utf-8'))
        #                 meta.update({'songid': res['pos']})
        #                 res.update({'metadata': meta})
        #             else:
        #                 self.numid.update({res: self.maxsongid})
        #             print(res)
        #             self.numid.update({self.maxsongid: res})
        #             return self.maxsongid
        if self.launching:
            d = task.deferLater(
                reactor, 0.5, self.insert, *(url, afterid, metadata))
            return d
        if not self.launched:
            print('*')
            self.launching = True
            threads.deferToThread(self.launch_player)
            d = task.deferLater(
                reactor, 0.5, self.insert, *(url, afterid, metadata))
            return d
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
        if self.has_tracklist:
            if len(self.playlist) == 0 or int(afterid) == 0:
                self.mediaplayer.call(
                    'AddTrack',
                    url,
                    dbus.ObjectPath(
                        '/org/mpris/MediaPlayer2/TrackList/NoTrackurl'),
                    True,
                    interf='org.mpris.MediaPlayer2.TrackList')
            else:
                self.mediaplayer.call(
                    'AddTrack',
                    url,
                    dbus.ObjectPath(self.numid[int(afterid)]),
                    True,
                    interf='org.mpris.MediaPlayer2.TrackList')
#             d.addCallback(get_newid)
#             d.addCallback(inserted, metadata)
            d = task.deferLater(reactor, 0.5, lambda: self.playlist[-1])
            d.addCallback(show)
            return d
        else:
            log.err('playlist length:%s' % len(self._playlist))
            self.maxsongid += 1
            if not isinstance(metadata, dict):
                try:
                    metadata = metadata.encode('utf-8')
                except:
                    log.err('utf8 issue: %s' % metadata)
                    metadata = metadata.decode('utf-8')
                metadata = didl_decode(metadata)
            metadata.update({'songid': str(self.maxsongid)})
            if len(self._playlist) == 0:
                self._playlist.append([self.maxsongid, url, metadata])
            else:
                self._playlist.insert(
                    self.playlist[self.playlist.index(int(afterid))],
                    [self.maxsongid, url, metadata])
            log.err('real playlist: %s' % self._playlist)
            self.playlist = [i[0] for i in self._playlist]
            log.err('new playlist: %s' % self.playlist)
            log.err('metadata dic: %s' % metadata)
            self.oh_playlist = [str(i) for i in self.playlist]
            self.idArray = id_array(self.playlist)
            self.changed_state('TrackList', {}, '')
            if self.songid == 0:
                self.songid = 1
            return defer.succeed(self.maxsongid)

    def delete(self, songid):
        if self.has_tracklist:
            self.mediaplayer.call(
                'RemoveTrack',
                dbus.types.ObjectPath(self.numid[int(songid)]),
                interf='org.mpris.MediaPlayer2.TrackList')
        else:
            try:
                suppressed = self.playlist.index(songid)
            except IndexError:
                pass
            else:
                self._playlist.pop(suppressed)
                self.playlist.pop(suppressed)
                self.idArray = id_array(self.playlist)
                self.changed_state('TrackList', {}, '')

    def clear(self):
        if self.has_tracklist:
            for track in self._playlist:
                self.mediaplayer.call(
                    'RemoveTrack',
                    track,
                    interf='org.mpris.MediaPlayer2.TrackList')
        else:
            self.playlist = []
            self._playlist = []
            self.songid = 0
            self.idArray = ''
            self.changed_state('TrackList', {}, '')


class PlayerProcess(protocol.ProcessProtocol):
    '''
    Manage player process
    '''
    def __init__(self, parent):
        self.parent = parent
        parent.protocol = self
        self.data = ''

    def connectionMade(self):
        #         log.msg("Process launched!")
        self.parent.juststarted = True
        self.parent.extpid = self.transport.pid
        #         log.msg(
        #         'dbus session address = %s'
        #          % os.getenv('DBUS_SESSION_BUS_ADDRESS'))
        self.transport.closeStdin()
        self.parent.launched = True
        self.parent.connect()

    def processEnded(self, reason):
        if reason.value.exitCode != 0:
            log.err("processEnded, status %s" % reason.value.exitCode)
        self.parent.connectionLost('Player process died')

    def shutdown(self):
        self.transport.loseConnection()


def show(res):
    log.err('**************%s***************' % res)
    return res
