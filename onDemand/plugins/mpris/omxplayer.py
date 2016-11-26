# encoding: utf-8
'''
Created on 29 oct. 2016

@author: Bertrand Verdu
'''
import os
import psutil
import math
from twisted.python.failure import DefaultException
from twisted.logger import Logger
from onDemand.protocols.dbus import ODbusProxy, get_user_sessions
from twisted.internet import task, reactor, defer, protocol
from onDemand.utils import upnptime_to_mpristime, Timer
from default import Default
from onDemand.utils import show, stringify

log = Logger()

__updated__ = ""


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

    def __init__(self, *args, **kwargs):

        #         self.playername = program
        super(Mpris_factory, self).__init__()
        self.polling = False
        if 'cmd' in kwargs:
            if args:
                #                 print(args)
                self.process_args = [kwargs['cmd']] + [
                    arg for arg in args.split()]
            else:
                self.process_args = [kwargs['cmd']]
            self.process_path = kwargs['cmd']
        self.process = PlayerProcess(self)
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
                self.tracklist.tracks = {}
                self.tracklist.tracklist = []
            self.connecting = False
            self.purge_actions()
            if self.timeout:
                self.timeout.cancel()
            for clbk in self.start_callbacks:
                clbk.callback(True)
            self.start_callbacks = []
            self.timeout = None

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
                        d.addCallbacks(lambda state: self.changed_state(
                            {"PlaybackStatus": state}),
                            self.call_failed,
                            errbackArgs=(
                            "Properties Get PlaybackStatus",))
                    d.addCallback(
                        lambda ignored: setattr(self, 'pending', False))
            reactor.callLater(5, self.poll_status)  # @UndefinedVariable

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
                offset = (newtime - self.seconds) * 1000000
            else:
                offset = int((float(newpos) - float(self.seconds)) * 1000000)
            d = self.player.Seek(offset)
            d.addCallbacks(transition, self.call_failed)
            return d

    def set_position_relative(self, pos, fmt='UPNP'):

        if self.process.launched:
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

    def play(self, speed=1, songid=None):

        log.debug('Play: %s' % str(songid))

        if songid is not None:
                #                 log.err(songid)
            uri = self.tracklist.tracks[songid][1]
            self.metadata = self.tracklist.tracks[songid][2]
            self.metadata_str = self.tracklist.tracks[songid][3]
            if self.player:
                d = self.player.Stop()
                d.addErrback(self.call_failed, "Stop")
                d.addBoth(lambda ignored:
                          task.deferLater(reactor,
                                          1,
                                          self.play,
                                          *(speed, songid)))
            else:
                d = self.launch_process(uri)
            d.addCallback(lambda ignored: self.changed_state(
                {'PlaybackStatus': 'Playing'}))
            return d
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

    '''
    UPNP wrapped functions
    '''

    '''
    AVTransport and OpenHome Playlist
    '''

    def r_id(self):
        log.debug('Id')
        return self.songid

    def r_pause(self, instanceID=0):
        log.debug('Pause')
        if self.player:
            d = self.player.Pause()
            d.addCallbacks(
                lambda ignored: self.changed_state(
                    {'PlaybackStatus': 'Paused'}),
                self.call_failed, errbackArgs=('Pause',))

    def r_stop(self, instanceID=0):
        if self.player:
            self.player.Stop()
        else:
            self.protocol.shutdown()

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
