'''
Created on 25 oct. 2016

@author: babe
'''
import os
import xml.etree.cElementTree as et
from twisted.logger import Logger
from twisted.internet import defer, task, utils, reactor
from upnpy_spyne.utils import didl_encode, didl_decode, id_array
from onDemand.utils import mpris_decode, stringify, upnptime_to_mpristime
from onDemand.protocols.dbus import ODbusProxy

log = Logger()


class Tracklist(object):

    parent = None

    def __init__(self):
        self.tracks = None
        self.tracklist = []
        self.maxsongid = 0
        self.repeat = False
        self.shuffle = False
        self.connected = False

    def updated(self):

        log.debug("updated")

        self.parent.idArray = id_array(self.tracklist)
        self.parent.oh_eventPLAYLIST(self.parent.idArray, 'idarray')
        if self.parent is not None:
            self.parent.remote_fct['active'] = bool(len(self.parent.idArray))

    def update(self, res=None):

        log.error('Don\'t update me !')
        raise NotImplementedError('Update called on disconnected Tracklist')

    def insert(self, afterid, url, metadata_str, current=False, checked=False):
        log.debug('Insert :%s  --  %s  --  %s' % (afterid, url, metadata_str))
        # return
        afterid = int(afterid)
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
                    u.split('\n')[0], afterid, metadata_str, current, True))
            return d
#         log.err('playlist length:%s' % len(self._playlist))
        metadata = didl_decode(metadata_str)[0]
        del metadata['metadata']
        if 'duration' in metadata:
            metadata['duration'] = upnptime_to_mpristime(metadata['duration'])
        self.maxsongid += 1
        metadata['trackid'] = unicode(str(self.maxsongid))
        if not self.tracks or len(self.tracklist) == 0:
            self.tracks = {self.maxsongid: [self.maxsongid, url, metadata,
                                            metadata_str]}
            self.tracklist = [self.maxsongid]
        else:
            self.tracks[self.maxsongid] = [self.maxsongid, url, metadata,
                                           metadata_str]
            if afterid == 0:
                self.tracklist.insert(0, self.maxsongid)
            elif afterid == -1:
                self.tracklist.append(self.maxsongid)
            else:
                self.tracklist.insert(
                    self.tracklist[self.tracklist.index(int(afterid))],
                    self.maxsongid)
        self.changed_tracks()
        return defer.succeed(self.maxsongid)

    def get_track(self, track):

        return defer.succeed((self.tracks[track][1], self.tracks[track][2],))

    def get_tracks(self, tracks):
        def format_result(res):
            tl = et.Element('TrackList')
            for (success, value) in res:
                if success:
                    en = et.Element('Entry')
                    i = et.Element('Id')
                    i.text = str(value[0])
                    en.append(i)
                    uri = et.Element('Uri')
                    uri.text = value[1].decode('utf-8')
                    en.append(uri)
                    md = et.Element('Metadata')
                    md.text = ''
#                     log.info(stringify(value[2]))
#                     print(value[2])
                    md.text = didl_encode(value[2])
                    en.append(md)
                    tl.append(en)
                else:
                    log.error(value.getErrorMessage())
            log.debug(et.tostring(tl))
            return et.tostring(tl)
        tr = []
        for track in tracks:
            tr.append((True,
                       (self.tracks[track][0],
                        self.tracks[track][1],
                        self.tracks[track][2],)))
        tracks = tr
        return defer.succeed(format_result(tr))

    def changed_tracks(self):
        log.debug('tracklist event')
        self.updated()

    def next(self, songid, step=1):

        ind = self.tracklist.index(int(songid)) + step

        if ind > len(self.tracklist):
            return self.tracklist[0] if self.repeat else None

        elif ind < 0:
            return self.tracklist[-1] if self.repeat else None
        else:
            return self.tracklist[ind]

    def delete(self, songid):
        #  log.err(self.playlist)
        if songid in self.tracklist:
            del self.tracks[songid]
            self.tracklist.remove(songid)
            self.changed_tracks()

    def clear(self):

        if len(self.tracklist) == 0:
            return
        self.tracks = None
        self.tracklist = []
        self.parent.songid = 0
        self.changed_tracks()


class MprisTracklist(ODbusProxy, Tracklist):
    '''
    Manage the tracks of the player
    If the player has its own tracklist,
    this class manage the translation in UPnP,
    otherwise a tracklist is managed locally
    '''

    def __init__(self, *args, **kwargs):
        super(MprisTracklist, self).__init__(*args, **kwargs)
        self.parent = None
        self.tracks = None
        self.tracklist = []
        self.maxsongid = 0
        self.repeat = False
        self.shuffle = False

    def update(self, res=None):
        log.debug("update...")
        if self.tracks is None:
            self.tracks = {}
            self.tracklist = []
            self.connected = True

        def got_tracks(tracks):
            deleted = self.tracks.keys()
            updated = False
            for i, track in enumerate(tracks, 1):
                if i > self.maxsongid:
                    self.maxsongid = i
                if track in self.tracks:
                    deleted.remove(track)
                    self.tracks[track][0] = i
                    if i in self.tracks:
                        deleted.remove(i)
                    self.tracks[i] = [track, self.tracks[track][1]]
                    try:
                        if self.tracklist[i - 1] != i:
                            updated = True
                            self.tracklist[i - 1] = i
                    except IndexError:
                        self.tracklist.append(i)
                        updated = True
                else:
                    if i in self.tracks:
                        self.tracks[track] = [i, self.tracks[i][1]]
                        self.tracks[i][0] = [track]
                        deleted.remove(i)
                    else:
                        self.tracks[track] = [i, {}]
                        self.tracks[i] = [track, {}]
                        self.tracklist.insert(i - 1, i)
                        updated = True

#                     print(self.tracks)
#                     print(self.tracklist)
            log.debug("to delete: %s" % stringify(deleted))
            for k in deleted:
                if isinstance(k, int) or k.isdigit():
                    log.debug("delete: %s" % str(k))
                    del self.tracks[k]
                    self.tracklist.remove(k)
                else:
                    log.debug("delete: %s" % k)
                    updated = True
                    del self.tracks[k]
            if updated:
                self.updated()
            return self.tracks
        d = self.parent.properties.Get('org.mpris.MediaPlayer2.TrackList',
                                       'Tracks')
        d.addCallback(got_tracks)
        return d

    def fake_insert(self, afterid, url, md):
        log.debug("Fake Insert...")
        self.maxsongid += 1
        self.tracks[self.maxsongid] = ['***' + url, md]
        self.tracks['***' + url] = [self.maxsongid, md]
        if afterid == 0:
            self.tracklist.insert(0, self.maxsongid)
        elif afterid == -1:
            self.tracklist.append(self.maxsongid)
        else:
            self.tracklist.insert(
                self.tracklist.index(afterid) + 1, self.maxsongid)
        self.updated()
#         print(self.tracks)
        return self.maxsongid

    def insert(self, afterid, url, metadata_str, current=False, checked=False):
        log.debug('Insert :%s  --  %s  --  %s' % (afterid, url, metadata_str))
        # return
        afterid = int(afterid)
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
                    u.split('\n')[0], afterid, metadata_str, current, True))
            return d
#         log.err('playlist length:%s' % len(self._playlist))
        metadata = didl_decode(metadata_str)[0]
        del metadata['metadata']
        if 'duration' in metadata:
            metadata['duration'] = upnptime_to_mpristime(metadata['duration'])

        def set_md(sid, md):
            self.tracks[sid][1].update(md)
            self.tracks[self.tracks[sid][0]][1].update(md)

        if not current and self.parent.playername == 'vlc':
            return self.fake_insert(afterid, url, metadata)
        if len(self.tracks) == 0 or afterid == 0:
            self.AddTrack(url,
                          '/org/mpris/MediaPlayer2/TrackList/NoTrack',
                          current)
        elif afterid == -1:
            self.AddTrack(url,
                          self.tracks[self.tracklist[-1]][0],
                          current)
        else:
            self.AddTrack(url,
                          self.tracks[int(afterid)][0],
                          current)
        d = task.deferLater(reactor,
                            2,
                            lambda: self.maxsongid)
        d.addCallback(set_md, metadata)
        return task.deferLater(reactor,
                               2,
                               lambda: self.maxsongid)

    def get_track(self, track):

        def got_md(md, tr):
            if len(md) > 0:
                d = mpris_decode(md[0])
                self.tracks[tr][1].update(d)
                self.tracks[self.tracks[tr][0]][1].update(d)
            else:
                log.warn('Player has no Metadata for track: %s' % str(tr))
            return (self.tracks[tr][1]['url'], self.tracks[tr][1])
        try:
            ind = self.tracks[track][0]
            log.debug('##################%s' % stringify(ind))
        except KeyError:
            log.error("bad index: %s \n\t%s\n%s" % (
                str(track), '\n\t'.join(
                    [": ".join(
                        [str(i),
                         self.tracks[i][0]]) for i in self.tracklist]),
                str(self.tracklist)))
            ind = self.tracks[self.tracklist[-1]][0]
        log.debug('##################%s' % stringify(ind))
        if self.parent.playername == 'vlc' and ind.startswith("***"):
            return got_md([], track)
        d = self.GetTracksMetadata([ind])
        # d.addCallback(show)
        d.addCallback(got_md, track)
        return d

    def get_tracks(self, tracks):
        def format_result(res):
            tl = et.Element('TrackList')
            for (success, value) in res:
                if success:
                    en = et.Element('Entry')
                    i = et.Element('Id')
                    i.text = str(value[0])
                    en.append(i)
                    uri = et.Element('Uri')
                    uri.text = value[1].decode("utf-8")
                    en.append(uri)
                    md = et.Element('Metadata')
                    md.text = ''
#                     log.info(stringify(value[2]))
#                     print(value[2])
                    md.text = didl_encode(value[2])
                    en.append(md)
                    tl.append(en)
                else:
                    log.error(value.getErrorMessage())
            log.debug(et.tostring(tl))
            return et.tostring(tl)
        tr = []

        def add_index(res, ind):
            return (ind, res[0], res[1])
        for track in tracks:
            d = defer.maybeDeferred(self.get_track, track)
            d.addCallback(add_index, track)
            tr.append(d)
        dl = defer.DeferredList(tr)
        dl.addCallback(format_result)
        return dl

    def changed_tracks(self):
        log.debug('tracklist event')
        log.debug('\n Actual tracks: \n\t%s' % '\n\t'.join(
            [": ".join([str(i),
                        self.tracks[i][0]]) for i in self.tracklist]))

        def got_tracks(tracks):
            log.debug(
                '\nNew tracks: \n\t%s' % '\n\t'.join(
                    [": ".join(
                        [str(i), tracks[i][0]]) for i in self.tracklist]))
        d = task.deferLater(reactor, 0.5, self.update)
        d.addCallback(got_tracks)
        return d

    def delete(self, songid):

        tid = self.tracks[songid][0]
        if self.parent.playername == 'vlc' and tid.startswith("***"):
            self.tracklist.remove(songid)
            del self.tracks[tid]
            del self.tracks[songid]
        else:
            self.RemoveTrack(tid)

    def clear(self):

        if len(self.tracklist) == 0:
            return
        for track in self.tracklist:
            self.delete(track)
