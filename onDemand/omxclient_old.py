'''
Created on 22 janv. 2015

@author: babe
'''
import psutil
import os
import signal
from fractions import Fraction
from twisted.application.service import Service
from twisted.internet import reactor,\
    protocol,\
    defer,\
    task
from twisted.python import log
from mpyris.mediaplayer import MediaPlayer
from onDemand.utils import mpristime_to_upnptime,\
    upnptime_to_mpristime,\
    dbus_func_failed,\
    mpris_decode
from upnpy.utils import didl_decode, didl_encode


class OmxPlayer(Service):
    '''
    Manage omxplayer through dbus mpris interface
    '''
    name = "OmxPlayer"
    launched = False
    cancelplay = False
    _state = "TRANSITIONING"
    _track_URI = ''
    _event = False
    _managed = False
    _errors = 0
    indirect = False
    client = False
    robj = False
    is_player = False
    _volume = 100
    notify = False
    _rate = "1"
    _mtlist = ''
    _muted = False
    reltime = '0:00:00'
    counter = 0
    metadata = {}
    _metadata = {}
    metadata_str = 'NOT_IMPLEMENTED'
#     metadata = 'NOT_IMPLEMENTED'
    playfunc = None
    mediaplayer = None

    def __init__(self, player_path, args=None):
        '''
        Constructor
        '''
        self.playercmd_args = args
        self.player_path = player_path
        self.player_args = [player_path]
        self.player = player_path.split("/")[-1]

    def startService(self):
        '''
        Check and launch player program
        '''
        self.launch_player()

    def launch_player(self, test=False):
        if self.playercmd_args is not None:
            self.player_args = [self.player_path]\
                + self.playercmd_args.split()
        for proc in psutil.process_iter():
            if proc.name() == self.player:
                log.msg('Player process found', loglevel='debug')
                self._managed = False
                self.extpid = proc.pid
                self.juststarted = False
                self.running = 1
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
                return
            if test:
                return False
        self._managed = True
#         try:
#             reactor.spawnProcess(  # @UndefinedVariable
#                 PlayerProcess(self),
#                 self.player_path,
#                 self.player_args,
#                 env=os.environ)
#         except:
#             log.err("Program unknown : %s" % self.player_args)

    def connect(self, first=True):
        '''
        Try to get dbus connection with player
        '''
        def gotPlayer(name):
            self.connected = True
            self.launched = True
            log.msg("got dbus connection with player")
            log.msg("player = %s" % name.encode('utf8'), loglevel='debug')
            self._errors = 0
            self.getStatus(True)

        def noPlayer(err):
            self.connected = False
            if self._errors > 5:
                self.launch_player(True)
                log.msg("maximum number of errors reached, \
                                killing player process")
                return
            self._errors += 1
            log.msg("get dbus client failed: %s" % err.getErrorMessage())
#             log.msg('Trying again...')
        if self.mediaplayer is None:
            self.mediaplayer = MediaPlayer(self.player)
        d = self.mediaplayer.connect()
        d.addCallbacks(gotPlayer, noPlayer)
        return d

    def disconnect(self, obj=None, reason=''):
        log.msg('dbus disconnected, reason=%s' % reason, loglevel='debug')
        self.set_state('STOPPED')

    def connectionLost(self, reason):
        self.disconnect(reason=reason)

    def getStatus(self, first=True):
        '''
        Setup initial status and Install notifications
        '''
        if first:
            self.notify = False
            try:
                self.mediaplayer.register_signal('PropertiesChanged',
                                                 self.changed_state)
            except:
                log.msg("dbus register signal not supported, polling...",
                        loglevel='debug')
                task.deferLater(reactor, 1, self.getStatus, False)
#                 self.getStatus(False)
            else:
                self.notify = True
                self.mediaplayer.register_signal('NameLost',
                                                 self.disconnect,
                                                 interf='org.freedesktop.DBus')
                log.msg("notify = OK", loglevel='debug')
                task.deferLater(reactor, 1, self.getStatus, False)
#                 self.getStatus(False)
        else:
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
                if not self.notify:
                    reactor.callLater(  # @UndefinedVariable
                        3,
                        self.getStatus,
                        False)
            else:
                if self.launch_player(True):
                    return self.getStatus(True)

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

    def checkPid(self):
        try:
            if self.extpid.poll() is None:
                reactor.callLater(3, self.checkPid)  # @UndefinedVariable
            else:
                #                 log.msg("ext process stopped")
                self.extpid = None
                self.launched = False
                self.set_state('STOPPED')
                self.connectionLost('Player process died')
        except:
            try:
                p = psutil.Process(self.extpid)
                del(p)
                reactor.callLater(3, self.checkPid)  # @UndefinedVariable
            except:
                self.extpid = None
                self.launched = False
#                 log.msg("ext process stopped: %s" % e)

    def changed_state(self, dbus_interface, msg, lst, pending=False):
        if pending:
            log.msg('pending', loglevel='debug')
            if not self._event:
                log.msg('cancelled', loglevel='debug')
                return defer.succeed(None)
        self._event = False
        log.msg('remote client %s changed state = %s' %
                (dbus_interface, msg), loglevel='debug')
        if 'PlaybackStatus' in msg.keys():
            if len(msg['PlaybackStatus']) > 1:
                self.set_state(msg['PlaybackStatus'])
        if 'Rate' in msg.keys():
            rate = msg['Rate']
            self._rate = str(
                Fraction(float(rate)).
                limit_denominator(1).
                numerator)\
                + "/"\
                + str(Fraction(float(rate)).
                      limit_denominator(1).denominator)
        if "Volume" in msg.keys():
            log.msg('volume changed', loglevel='debug')
            vol = int(float(msg["Volume"])*100)
            if vol != self._volume:
                if vol != 0:
                    self._volume = int(float(msg["Volume"])*100)
                    self._muted = False
                else:
                    self._muted = True
                log.msg('send volume', loglevel='debug')
                self.upnp_eventRCS(
                    {'evtype': 'last_change',
                     'data':
                        [{'vname': 'Volume',
                          'value':
                            {'channel': 'Master',
                             'val': self._volume}},
                         {'vname': 'Mute',
                            'value':
                            {'channel': 'Master',
                             'val': int(self._muted)}}]})
        if 'Metadata' in msg.keys():
            self.update_metadata(msg['Metadata'])

    def update_metadata(self, metadata):
        if metadata != self._metadata:
            self._metadata.update(metadata)
            self.metadata.update(mpris_decode(metadata))
            if 'mpris:length' in metadata.keys():
                    ln = int(metadata['mpris:length'])
                    if ln < 1:
                        self._track_duration = "0:00:00"
                    else:
                        self._track_duration = mpristime_to_upnptime(ln)
                    log.msg('track length: %s'
                            % self._track_duration, loglevel='debug')
            if 'xesam:url' in metadata.keys():
                    self._track_URI = metadata['xesam:url']
                    self.metadata_str = didl_encode(self.metadata)

    def set_metadata(self, metadata):
        if (metadata != self.metadata) and (len(metadata) > 0):
            self.metadata.update(metadata)
            if 'duration' in metadata.keys():
                self._track_duration = metadata['duration']
            if 'url' in metadata.keys():
                self._track_URI = metadata['url']

    def set_state(self, state):
        log.msg("SET NEW STATE : %s " % state, loglevel='debug')
        if state in ['Stop', 'Play', 'Pause']:
            return defer.succeed(None)
        if state == "Paused":
            state = "PAUSED_PLAYBACK"
        else:
            self.cancelplay = False
        if state.upper() != self._state:
            self._state = str(state.upper())
            log.msg('send new state: %s' % self._state, loglevel='debug')
            self.prepare_event('upnp_eventAV')
            self.upnp_eventAV(
                {'evtype': 'last_change',
                 'data': [{'vname':
                           'TransportState',
                           'value': {'val': self._state}}]})
        else:
            return defer.succeed(None)

    def set_mimetypes(self, mtlist):
        #         log.msg("mtlist: % s" % mtlist)
        if self._mtlist != mtlist and len(mtlist) > 0:
            self._mtlist = mtlist
            self.upnp_eventCM({
                'evtype': 'sink_protocol_info',
                'data': [{'vname': 'SinkProtocolInfo',
                          'value': {'text': 'http-get:*:'+''
                                    .join([':*,http-get:*:'
                                           .join(mtlist)])+':*'}}]})

    def upnp_eventAV(self, evt):
        raise NotImplementedError()

    def upnp_eventCM(self, evt):
        raise NotImplementedError()

    def upnp_eventRCS(self, evt):
        raise NotImplementedError()

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

    def get_track(self):
        if self._state == 'STOPPED':
            track = 0
        else:
            track = 1
        return track

    def get_relcount(self):
        return 2147483647

    def get_abscount(self):
        return 2147483647

    def get_abstime(self):
            return '00:00:00'

    def endprocess(self):
        try:
            self._self.protocol.shutdown()
        except AttributeError:
            try:
                os.kill(self.extpid, signal.SIGINT)
            except Exception, e:
                log.err("endprocess failure : %s" % e.message)
            self.stopping = False

    def get_reltime(self):
        def setCounter(counter):
            self.counter = counter
            return self.counter

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
#                     loglevel='debug')
#                 reactor.callLater(1, self.get_reltime)#@UndefinedVariable
        return self.reltime

    def set_position(self, newpos):
        if self.launched:
            def transition(obj):
                current_state = self._state
                self.set_state('TRANSITIONING')
                reactor.callLater(  # @UndefinedVariable
                    0.5,
                    self.set_state,
                    current_state)
            curtime = upnptime_to_mpristime(self.reltime)
            newtime = upnptime_to_mpristime(newpos)
            offset = newtime - curtime
            d = self.mediaplayer.call('Seek', offset)
            d.addCallbacks(transition, dbus_func_failed,
                           errbackArgs=('Seek %d' % offset,))
            return d
        else:
            if self.launch_player(True):
                return self.set_position(newpos)

    def stop(self):
        def stopped(ret):
                self.set_state('STOPPED')
        if self._state != 'STOPPED':
            d = self.mediaplayer.call('Stop')
            self.reltime = '00:00:00'
            d.addCallbacks(stopped, dbus_func_failed,
                           errbackArgs=('Stop',))
            return d

    def guess_play_func(self):
        # omxplayer fix
        def playfuncplay(result):
            print('play')
            self.playfunc = 'Play'
            return result

        def playfuncpause(err):
            print('pause')
            self.playfunc = 'Pause'

        d = self.mediaplayer.call('Play')
        d.addCallbacks(playfuncplay, playfuncpause)
        return d

    def play(self, ignored=None):
        if self.launched:
            #  print('launched')
            print('from %s to Playing' % self._state)
            if (self._state in ['PAUSED_PLAYBACK', 'TRANSITIONING']):
                d = self.mediaplayer.call('Pause')
                d.addCallbacks(self.playing,
                               dbus_func_failed,
                               errbackArgs=(self.playfunc,))
                return d
            else:
                d = self.protocol.shutdown()
                d.addCallback(self.play)
        else:
            log.msg('launching player', loglevel='debug')
            reactor.spawnProcess(  # @UndefinedVariable
                PlayerProcess(self),
                self.player_path,
                self.player_args+[self._track_URI],
                env=os.environ)
            self._managed = True

    def playing(self, *ret):
            log.msg('playing...', loglevel='debug')
            self.set_state('PLAYING')

    def playpause(self):
        if self._state == 'PAUSED_PLAYBACK':
            return self.play()
        else:
            return self.pause()

    def pause(self):
        if self.launched:
            def paused(ret):
                if self._state in ['PLAYING', 'RECORDING']:
                    self.set_state('Paused')
    #         d =  self.player_func('Pause','org.mpris.MediaPlayer2.Player' )
            d = self.mediaplayer.call('Pause')
            d.addCallbacks(paused,
                           dbus_func_failed,
                           errbackArgs=('Pause',))
            return d
        else:
            if self.launch_player(True):
                return self.pause()

    def get_volume(self):
        if self.launched:
            def noVolume(err):
                if self._muted:
                    return 0
                else:
                    return self._volume

            def convert_volume(vol):
                self._volume = int(float(vol)*100)
                log.msg("volume= %d" % self._volume, loglevel='debug')
                return self._volume

            d = self.mediaplayer.get("Volume",
                                     interf='org.mpris.MediaPlayer2.Player')
            d.addCallbacks(convert_volume, noVolume)
            return d
        else:
            if self.launch_player(True):
                return self.get_volume()

    def set_volume(self, channel, volume):
        print("channel=%s volume= %s" % (channel, volume))
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

    def set_track_URI(self, uri, md=''):
        log.msg("set track uri : %s " % uri, loglevel='debug')
        try:
            log.msg("current uri : %s " % self._track_URI, loglevel='debug')
        except:
            pass
        if uri != self._track_URI:
            self._track_URI = uri
            self.metadata_str = md
            self.set_metadata(didl_decode(md.encode('utf8')))
            self.stop()
            reactor.callLater(0.5,  # @UndefinedVariable
                              self.play)


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
        #         self.parent.launched = True
        self.parent.connect()

    def processEnded(self, reason):
        if reason.value.exitCode != 0:
            log.err("processEnded, status %s" % reason.value.exitCode)
        self.parent.set_state('stopped')
        self.parent.launched = False
        self.parent.connectionLost('Player process died')

    def shutdown(self):
        self.transport.loseConnection()
