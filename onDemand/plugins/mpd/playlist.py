# encoding: utf-8
'''
Created on 31 août 2015

@author: Bertrand Verdu
'''
import os
import glob
from lxml import etree as et
from twisted.logger import Logger
from twisted.internet import defer, reactor, task
from upnpy_spyne.utils import didl_encode, id_array
from onDemand.utils import mpd_decode, upnptime_to_mpdtime

log = Logger()


class Playlist(object):
    '''
    classdocs
    '''
    length = 0
    coverdict = {}

    def __init__(self, mpd):
        '''
        Constructor
        '''
        self.length = 0
        self.mpd = mpd
        self.tracks = []
        self.details = []
        self.idarray = []
        self.track = None
        self.trackindex = -1
        self.plsversion = '0'

    def current_track(self, tid=None):
        log.debug('songid: %s' % tid)
        if not tid:
            return self.track
        tid = int(tid)
        if tid == self.trackindex:
            return
        if tid in self.tracks:
            self.trackindex = tid
            if len(self.details) != len(self.tracks):
                log.debug('details: %s tracks: %s' %
                          (len(self.details), len(self.tracks)))
                reactor.callLater(  # @UndefinedVariable
                    1, self.current_track, tid)
                return
            t, d = self.details[self.tracks.index(tid)]
            url, md = (c.text for c in t.getchildren()[1:3])
            self.track = (url, md,)
            self.mpd.trackcount += 1
            self.mpd.detailscount = 0
            self.mpd.metatextcount = 0
            self.mpd.songid = str(tid)
            self.mpd.upnp_eventAV(tid, 'currenttrack')
            self.mpd.oh_eventPLAYLIST(tid, 'id')
            self.mpd.oh_eventTIME(self.mpd.trackcount, 'trackcount')
            self.mpd.oh_eventINFO(self.mpd.trackcount, 'trackcount')
            if self.mpd.timer:
                self.mpd.timer.set()
            if 'duration' in d:
                self.mpd._track_duration = d['duration']
                sec = upnptime_to_mpdtime(d['duration'])
                self.mpd.ohduration = sec
                log.debug('duration=%s' % sec)
                self.mpd.upnp_eventAV(d['duration'], 'currenttrackduration')
                self.mpd.oh_eventINFO(sec, 'duration')
                self.mpd.oh_eventTIME(sec, 'duration')
            if 'url' in d:
                self.mpd._track_URI = d['url']
                self.mpd.upnp_eventAV(d['url'], 'avtransporturi')
                self.mpd.oh_eventINFO(d['url'], 'uri')
                self.mpd.upnp_eventAV(d['url'], 'currenttrackuri')
                if 'codec' in d:
                    self.mpd.oh_eventINFO(
                        d['codec'].upper(), 'codecname')
                    if d['codec'].lower() in ['flac', 'm4a']:
                        self.mpd.lossless = True
                        self.mpd.oh_eventINFO(1, 'lossless')
                    else:
                        self.mpd.lossless = False
                        self.mpd.oh_eventINFO(0, 'lossless')
                    self.mpd.codecname = d['codec'].upper()
            self.mpd.metadata_str = t.getchildren()[2].text
            self.mpd.oh_eventINFO(self.mpd.metadata_str, 'metadata')
            self.mpd.upnp_eventAV(
                self.mpd.metadata_str, 'avtransporturimetadata')
            if self.mpd.tracksmax == 0:
                self.mpd.tracksmax = 10000
                self.mpd.oh_eventPLAYLIST(1000, 'tracksmax')
        else:
            reactor.callLater(1, self.current_track, tid)  # @UndefinedVariable

    def update(self, data, tid=None):

        dd = defer.Deferred()
        log.debug('update requested')  # : %s %s' % (data, self.length))

        def updated(res):
            log.debug('playlist updated')
            if len(self.tracks) > 0:
                self.mpd.idArray = id_array(self.tracks)
                self.mpd.oh_eventPLAYLIST(self.mpd.idArray, 'idarray')
                self.plsversion = self.mpd.status['playlist']
                if tid:
                    if int(tid) in self.tracks:
                        dd.callback(tid)
                    else:
                        dd.errback()

        def format_track(track):

            en = et.Element('Entry')
            i = et.Element('Id')
            if 'id' not in track:
                log.critical('issue with playlist :%s' % track)
            i.text = track['id']
            en.append(i)
            uri = et.Element('Uri')
            uri.text = track['url'].decode('utf-8')
            en.append(uri)
            md = et.Element('Metadata')
            md.text = didl_encode(track)
            en.append(md)
            return (en, track,)

        def setter(res, pos):
            # print('playlist detail: %s %s' % (pos, res))
            self.details[pos] = res

        if data is not None:
            if not isinstance(data, list):
                data = [data]
            if self.length == 0:
                log.debug('empty')
                self.tracks = []
                self.details = []
                return
            else:
                l = []
                delta = self.length - len(self.tracks)
                # print('delta= %d' % delta)
                if delta >= 0:
                    for track in data:
                        #                         self.cache_cover(track)
                        try:
                            if int(track['Pos']) >= len(self.tracks):
                                self.tracks.append(int(track['Id']))
                                d = self.mpd.call('playlistid', track['Id'])
                                d.addCallback(self.get_cover, track['Id'])
                                d.addCallback(mpd_decode)
                                d.addCallback(format_track)
                                d.addCallback(self.details.append)
                            else:
                                self.tracks[int(
                                    track['Pos'])] = int(track['Id'])
                                d = self.mpd.call('playlistid', track['Id'])
                                d.addCallback(self.get_cover)
                                d.addCallback(mpd_decode)
                                d.addCallback(format_track)
                                d.addCallback(setter, int(track['Pos']))
                            l.append(d)
                        except:
                            continue
                else:
                    for track in data:
                        if 'Id' not in track:
                            continue
                        if track == {}:
                            self.tracks.pop()
                            self.details.pop()
                            delta += 1
                            continue
                        if delta < 0:
                            self.tracks.pop(int(track['Pos']))
                            self.details.pop(int(track['Pos']))
                            delta += 1
                        else:
                            self.tracks[int(track['Pos'])] = int(track['Id'])
                            d = self.mpd.call('playlistid', track['Id'])
                            d.addCallback(self.get_cover)
                            d.addCallback(mpd_decode)
                            d.addCallback(format_track)
                            d.addCallback(setter, int(track['Pos']))
                            l.append(d)
                if len(l) > 0:
                    dl = defer.gatherResults(l, consumeErrors=False)
                    dl.addCallback(updated)
        else:
            log.warn('Playlist update request returned no data')
        if tid:
            return dd
        else:
            dd = None

    def get_tracks(self, tracks):

        tl = et.Element('TrackList')
        for track in tracks:
            #             print(self.playlist.index(int(track)))
            #             print(len(self.playlist), len(self.playlist_details))
            try:
                tl.append(
                    self.details[self.tracks.index(int(track))][0])
            except ValueError:
                log.debug('ouye!!!')
                return task.deferLater(reactor, 3, self.get_tracks, tracks)
        r = et.tostring(tl)
        log.debug('tracklist generated')
        return r

    def get_track(self, track=None):

        if track is None:
            return self._track_URI, self.metadata_str
        else:
            res = self.details[self.tracks.index(int(track))][0]
            url, md = (c.text for c in res.getchildren()[1:3])
            return url, md

    def cache_cover(self, track):
        if 'file' in track:
            if track['file'] in self.coverdict:
                if self.coverdict[track['file']]:
                    return
            imglist = glob.glob(os.path.join(
                self.mpd.cover_dir,
                os.path.split(track['file'])[-2],
                '*.[p,j][p,n][g]'))
            if len(imglist) > 0:
                for p in imglist:
                    if p.startswith('cover'):
                        url = p
                        break
                    elif p.startswith('front'):
                        url = p
                        break
                else:
                    url = imglist[0]
            else:
                url = None
            log.debug(
                'url for {file} cached:{url}', file=track['file'], url=url)
            self.coverdict.update({track['file']: url})

    def get_cover(self, track, tid=None):
        if isinstance(track, list):
            d = {}
            for dic in track:
                d.update(dic)
            track = d
            # print('concatened: %s' % track)
#         if self.mpd.net_type in ('cloud', 'both'):
#             url = None
#             track.update({'albumArtURI': url})
#             self.coverdict.update({track['file']: url})
#             return track
        if 'Id' not in track:
            if tid:
                track.update({'Id': tid})
            else:
                log.debug('no id')
        if 'file' in track:
            if track['file'] in self.coverdict:
                if self.coverdict[track['file']]:
                    track.update(
                        {'albumArtURI': self.coverdict[track['file']]})
                    log.debug('cached: %s' % track['albumArtURI'])
                return track
            d = os.path.split(track['file'])[-2]
            for char in ['[', ']', '?', '*']:
                # workaround for excape regex chars
                if char in d:
                    i = d.index(char)
                    d = d[:i] + '[' + d[i] + ']' + d[i + 1:]
#                     log.error(d)
            imglist = glob.glob(os.path.join(
                self.mpd.cover_dir,
                d,
                "*.[p,j][p,n][g]"))
            if len(imglist) > 0:
                for p in imglist:
                    if p.startswith('cover'):
                        f = p
                        break
                    elif p.startswith('front'):
                        f = p
                        break
                else:
                    f = imglist[0]
                if self.mpd.net_type in ('cloud', 'both'):
                    url = self.mpd.parent.parent.register_art_url(
                        f, cloud=True)
                else:
                    url = self.mpd.parent.parent.register_art_url(f)
                    log.debug('%s --> %s' % (f, url))
                track.update({'albumArtURI': url})
            else:
                url = None
            self.coverdict.update({track['file']: url})
        return track
