# -*- coding: utf-8 -*-
'''
Created on 29 déc. 2014

@author: Bertrand Verdu
'''
import os
from twisted.application import internet
from twisted.internet import defer, reactor, utils
from twisted.python import log

from onDemand.protocols.mpd import MpdFactory
from upnpy.utils import didl_decode, didl_encode, id_array
from onDemand.utils import Timer, \
    mpd_decode, \
    mpdtime_to_upnptime, \
    upnptime_to_mpdtime
import xml.etree.cElementTree as et


# import config
class Mpdclient(internet.TCPClient):  # @UndefinedVariable
    '''
    classdocs
   '''
    _state = "pending"
    upnp_state = "TRANSITIONNING"
    oh_state = 'Buffering'
    _track_URI = ''
    _managed = False
    _errors = 0
    _metadata = {}
    _playlist = []
    _volume = 100
    _rate = "1"
    _mtlist = ''
    mtlist = ''
    _muted = True
    _track_duration = '0:00:00.000'
    name = "MpdPlayer"
    cancelplay = False
    reltime = '0:00:00.000'
    seconds = 0
    repeat = False
    shuffle = False
    counter = 0
    tracksmax = 0
    metadata = {}
    playlist = []
    idArray = ''
    maxid = 0
    metadata_str = 'NOT_IMPLEMENTED'
    songid = 0
    transport_actions = ['PLAY']
    timer = None
    token = 0
    max_volume = 100

    def __init__(self, addr='127.0.0.1', port='6600', **kwargs):
        '''
        Constructor
        '''
        self.addr = addr
        print addr
        print port
        self.port = int(port)
        self.mpd = MpdFactory(self.changed_state)
        internet.TCPClient.__init__(self,  # @UndefinedVariable
                                    addr,
                                    self.port,
                                    self.mpd)

    def startService(self):
        internet.TCPClient.startService(self)  # @UndefinedVariable
        self.update_state()
        self.update_metadata()
        self.update_mimetypes()

    def changed_state(self, state):
        changed = state.keys()
        if 'state' in changed:
            self.set_state(state['state'])
        if "volume" in changed:
            log.msg('volume changed', loglevel=logging.DEBUG)
            vol = int(state['volume'])
            if vol != self._volume:
                if vol != 0:
                    self._volume = vol
                    muted = False
                else:
                    muted = True
                log.msg('send volume', loglevel=logging.DEBUG)
                self.oh_eventVOLUME(self._volume, 'volume')
                self.upnp_eventRCS(self._volume, 'Volume')
                if muted is not self._muted:
                    self._muted = muted
                    self.upnp_eventRCS(self._muted, 'Mute')
                self.oh_eventVOLUME(int(self._muted), 'mute')

        if 'songid' in changed:
            self.update_metadata(state['songid'])
        if 'repeat' in changed:
            if self.repeat != bool(state['repeat']):
                self.repeat = bool(state['repeat'])
                if not self.shuffle:
                    self.upnp_eventAV(
                        'REPEAT_ALL' if self.repeat else 'NORMAL',
                        'CurrentPlayMode')
                else:
                    self.upnp_eventAV('REPEAT_ALL SHUFFLE' if self.repeat
                                      else 'NORMAL SHUFFLE', 'CurrentPlayMode')
                self.oh_eventPLAYLIST(self.repeat, 'repeat')
        if 'random' in changed:
            if self.shuffle != bool(state['repeat']):
                self.shuffle = bool(state['repeat'])
                if not self.repeat:
                    self.upnp_eventAV(
                        'NORMAL SHUFFLE' if self.shuffle else 'NORMAL',
                        'CurrentPlayMode')
                else:
                    self.upnp_eventAV(
                        'REPEAT_ALL SHUFFLE' if self.shuffle
                        else 'NORMAL SHUFFLE', 'CurrentPlayMode')
                self.oh_eventPLAYLIST(self.shuffle, 'shuffle')
        if 'elapsed' in changed:
            if self.timer is not None:
                self.timer.set(float(state['elapsed']))
        if 'playlist' in changed:
            self.token = int(state['playlist'])
        if 'playlistdata' in changed:
            self.update_playlist(state['playlistdata'])
        if 'bitrate' in changed:
            self.oh_eventINFO(int(state['bitrate']), 'bitrate')
        if 'audio' in changed:
            try:
                sr = int(state['audio'].split(':')[0])
                self.oh_eventINFO(sr, 'samplerate')
            except:
                log.err('Bad Samplerate: %s' % state['audio'].split(':')[0])
            try:
                bd = int(state['audio'].split(':')[1])
                self.oh_eventINFO(bd, 'bitdepth')
            except:
                log.err('Bad Bitdepth: %s' % state['audio'].split(':')[1])

    def update_state(self):
#         log.err('Update State: %s' % self.mpd.status['state'])
        self.set_state(self.mpd.status['state'])

    def update_playlist(self, newpl):
        self.playlist = newpl
        self.idArray = id_array(newpl)
        self.oh_eventPLAYLIST(self.idArray, 'idarray')
#         d.addCallback(self.oh_eventPLAYLIST, 'idarray')

    def update_metadata(self, songid=None):
        log.msg('update metadata')

        def getmd(md):
            if isinstance(md, list):
                nd = {}
                for d in md:
                    nd.update(d)
                md = nd
            if md != self._metadata:
                self._metadata = md
#                 log.err(md)
                self.metadata.update(mpd_decode(self._metadata))
                if self._track_duration != self.metadata['duration']:
                    self._track_duration = self.metadata['duration']
                    self.upnp_eventAV(self._track_duration,
                                      'CurrentTrackDuration')
                    sec = upnptime_to_mpdtime(self._track_duration)
                    self.oh_eventINFO(sec, 'duration')
                    self.oh_eventTIME(sec, 'duration')
                if self.songid != self.metadata['id']:
                    self.songid = self.metadata['id']
                    self.upnp_eventAV(int(self.songid), 'CurrentTrack')
                    self.oh_eventPLAYLIST(int(self.songid), 'id')
                    self.oh_eventTIME(1, 'trackcount')
                if 'url' in self.metadata.keys():
                    self._track_URI = self.metadata['url']
                    self.upnp_eventAV(self._track_URI, 'AVTransportURI')
                    self.oh_eventINFO(self._track_URI, 'uri')
                    self.upnp_eventAV(self._track_URI, 'CurrentTrackURI')
                    try:
                        self.oh_eventINFO(
                            self.metadata['codec'].upper(), 'codecname')
                        if self.metadata['codec'].lower() in ['flac', 'm4a']:
                            self.oh_eventINFO(1, 'lossless')
                        else:
                            self.oh_eventINFO(0, 'lossless')
                    except KeyError:
                        pass
                self.metadata_str = didl_encode(self.metadata)
                self.oh_eventINFO(self.metadata_str, 'metadata')
                self.upnp_eventAV(self.metadata_str, 'AVTransportURIMetaData')
                if self.tracksmax == 0:
                    self.tracksmax = 10000
                    self.oh_eventPLAYLIST(self.tracksmax, 'tracksmax')

        if songid is not None:
            d = self.mpd.call('playlistid', songid)
        else:
            d = self.mpd.call('currentsong')
        d.addCallback(getmd)

    def update_mimetypes(self):
        self.set_mimetypes(self.mpd.mimetypes)

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
        return self.mpd.call('playlistid', self.mpd.status['songid'])

    def getMimeTypes(self):
        return self.mpd.call('decoders')

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

        d = self.mpd.call('sticker', ' '.join(('list song', url.join('"'*2))))
        d.addBoth(got_sticker, dic)
        return d

    def get_tracks(self, tracks):

        def got_tracks(tracks):
            if not isinstance(tracks, list):
                tracks = [tracks]
            sl = []
            for track in tracks:
                t = mpd_decode(track)
                sl.append(self.get_sticker(t['url'], t))
            return defer.gatherResults(sl)

        def generate_tracklist(tracks, tracklist=None):
#             log.err(tracks)
            if not isinstance(tracks, list):
                tracks = [tracks]
            tl = et.Element('TrackList')
            for idx, track in enumerate(tracks):
#                 log.err(track)
                if isinstance(track, dict):
                    track = mpd_decode(track)
                else:
#                     log.err(track)
                    nd = {}
                    for d in track:
#                         log.err(d)
                        nd.update(d)
                    track = mpd_decode(nd)
#                     log.msg(nd)
                en = et.Element('Entry')
                i = et.Element('Id')
                if not 'id' in track:
                    if tracklist:
                        track.update({'id': str(tracklist[idx])})
                    else:
                        log.err(track)
                i.text = track['id'].decode('utf-8')
                en.append(i)
                uri = et.Element('Uri')
                uri.text = track['url'].decode('utf-8')
                en.append(uri)
                md = et.Element('Metadata')
                md.text = didl_encode(track)
                en.append(md)
                tl.append(en)
            return et.tostring(tl)

#         if tracks == self.playlist:
#             d = self.mpd.call('playlistid')
#             d.addCallback(generate_tracklist, tracks)
#         else:
        tl = []
        for track in tracks:
            tl.append(self.mpd.call('playlistid', str(track)))
        d = defer.gatherResults(tl)
#         d.addCallback(got_tracks)
        d.addCallback(generate_tracklist)
        return d

    def get_track(self, track=None):

        def got_result(res):
            uri = res['url']
            return (uri, didl_encode(res))
        if track is None:
            d = defer.succeed((self._track_URI, self.metadata_str))
        else:
            d = self.mpd.call('playlistid', str(track))
            d.addCallback(mpd_decode)
            d.addCallback(got_result)
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
#         log.err('reltime: %s' % t)
        return t

    def get_volume(self):

        def noVolume(err):
            if self._muted:
                return 0
            else:
                return self._volume

        def convert_volume(vol):
            self._volume = int(float(vol) * 100)
            log.msg("volume= %d" % self._volume, loglevel=logging.DEBUG)
            return self._volume

        d = self.mediaplayer.get("Volume",
                                 interf='org.mpris.MediaPlayer2.Player')
        d.addCallbacks(convert_volume, noVolume)
        return d

    def get_transport_actions(self):
            return {','.join(self.transport_actions)}

    def set_volume(self, channel, volume):
        volume = str(volume)
        d = self.mpd.call('setvol', volume)
        d.addErrback(
            log.msg,
            'Set Volume Error : %s - %d' % (channel, int(volume)))
        reactor.callLater(0.1,  # @UndefinedVariable
                          self.changed_state,
                          {'volume': str(volume)})

    def set_mimetypes(self, mtlist):
        if self._mtlist != mtlist:
            self._mtlist = mtlist
            self.mtlist = 'http-get:*:' + ''\
                .join([':*,http-get:*:'.join(mtlist)]) + ':*'
            self.upnp_eventCM(self.mtlist, 'SinkProtocolInfo')
            self.oh_eventPLAYLIST(self.mtlist, 'protocolinfo')

    def set_metadata(self, metadata):
        if metadata != self.metadata:
            self.metadata.update(metadata)
            if 'duration' in metadata.keys():
#                 log.err('duration set to %s by metadata'
#                         % metadata['duration'])
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
        log.msg("SET NEW STATE : %s " % state, loglevel=logging.DEBUG)
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
                d = self.mpd.call('status')
                d.addCallback(lambda st: st['elapsed'])
                d.addCallbacks(
                    self.set_reltime,
                    lambda ignored: self.set_reltime(self.timer.get()))
            self.upnp_state = 'PAUSED_PLAYBACK'
            self.oh_state = 'Paused'
        elif state == 'play':
            self.transport_actions = ['STOP', 'PAUSE', 'SEEK']
            self.changed_state({'volume': self.mpd.status['volume']})
            self.timer = Timer()
            self.timer.set(self.seconds)
            d = self.mpd.call('status')
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
#             log.err('Unknow State from player : %s' % state)
            return
        log.msg('send new state: %s' % self._state, loglevel=logging.DEBUG)
        self.upnp_eventAV(self.upnp_state, 'TransportState')
        self.oh_eventPLAYLIST(self.oh_state, 'transportstate')

    def set_songid(self, songid):
        self.songid = songid['Id']
#         log.err('songid = %s' % songid)
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
        d = self.mpd.call('seekcur', pos)
        d.addCallback(transition)
        return d

    def set_position_relative(self, delta, fmt='UPNP'):
        newpos = int(self.get_reltime('Seconds')) + int(delta)
        self.set_position(newpos, fmt)

    def set_track_URI(self, uri, md=''):
        log.msg("set track uri : %s " % uri, loglevel=logging.DEBUG)
        try:
            log.msg("current uri : %s " % self._track_URI, loglevel=logging.DEBUG)
        except:
            pass
        if uri != self._track_URI:
            self._track_URI = uri
            self.metadata_str = md
            self.set_metadata(didl_decode(md.encode('utf-8')))
            d = self.mpd.call('addid', uri)
            d.addCallback(self.set_songid)
            d.addCallback(self.play)

    def set_repeat(self, repeat):
        self.mpd.call('repeat', str(int(repeat)))

    def set_shuffle(self, repeat):
        self.mpd.call('shuffle', str(int(repeat)))

    def stop(self):
        def stopped(ret):
                self.set_state('stop')
        if self._state != 'STOPPED':
            d = self.mpd.call('stop')
            self.reltime = '00:00:00'
            d.addCallback(stopped)

    def play(self, songid=None, ignored=None):
        def success(result):
            return None
        if self.cancelplay:
            self.cancelplay = False
        else:
            if songid is not None:
                d = self.mpd.call('playid', songid)
            else:
                if self._state == 'pause':
                    d = self.mpd.call('pause', '0')
                else:
                    d = self.mpd.call('playid', self.songid)
            d.addCallback(self.playing)

    def playing(self, *ret):
            log.msg('playing...', loglevel=logging.DEBUG)
            self.set_state('play')

    def playindex(self, index):
        return self.play(self.playlist[int(index)])

    def playpause(self):
        if self._state == 'pause':
            return self.play()
        else:
            return self.pause()

    def pause(self):
        def paused(ret):
            if self._state == 'play':
                self.set_state('pause')
    #         d =  self.player_func('Pause','org.mpris.MediaPlayer2.Player' )
        d = self.mpd.call('pause', '1')
        d.addCallback(paused)
        return d

    def next(self):
        self.mpd.call('next')

    def previous(self):
        self.mpd.call('previous')

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
            return self.set_volume('Master', '0')

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
                    float(i)/2,
                    self.mpd.call,
                    ' '.join(('sticker',
                              'set song',
                              dic['url'].join('"'*2),
                              tag,
                              '"' + dic[tag] + '"')))

    def insert(self, url, afterid, metadata, checked=False):

        def inserted(res, md):
            #             log.err('%s %s' % (res, md))
            #             reactor.callLater(2,  # @UndefinedVariable
            #                               self.insert_metadata,
            #                               md)
            return res['Id']

        if 'youtube' in url and not checked:
            # eclipse workaround !!!
            y = os.environ
            y.update({'PYTHONPATH': '/usr/bin/python'})
            # / eclipse workaround
            d = utils.getProcessOutput(
                '/usr/bin/youtube-dl',
                ['-g', '-f', 'bestaudio', url],
                env=y,
                reactor=reactor)
            d.addCallback(
                lambda u: self.insert(
                    u.split('\n')[0], afterid, metadata, True))
            return d
        if len(self.playlist) == 0:
            d = self.mpd.call('addid', url)
        elif int(afterid) == 0:
            d = self.mpd.call('addid', url + ' 0')
        else:
            d = self.mpd.call(
                'addid',
                ' '.join((url, str(self.playlist.index(int(afterid))+1))))
        d.addCallback(inserted, metadata)

        return d

    def delete(self, songid):
        self.mpd.call('deleteid', str(songid))

    def clear(self):
        self.mpd.call('clear')


if __name__ == '__main__':
    def show(res):
        print(res)
        return str(res)
    m = Mpdclient('192.168.0.9')
    m.startService()
    t = m.insert('https://www.youtube.com/watch?v=bsqLi9LfiwM', '1', '')
    print(m.playlist)
    t.addCallback(show)
    t.addCallback(m.play)
    t.addCallback(lambda r: reactor.stop())  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
