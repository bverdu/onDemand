#!/usr/local/bin/python2.7
# encoding: utf-8
'''
Created on 4 févr. 2015

@author: babe
'''
import os
import psutil
from gi.repository import GObject, Gio, GLib  # @UnresolvedImport
from twisted.internet import defer, task
from twisted.internet.threads import deferToThread
from twisted.python import log
# only for tests
# from twisted.internet import gireactor
# gireactor.install()
from twisted.internet import reactor


class Async_call_decorate(object):

    indirect = False
    arg_start = []
    arg_end = []

    def __init__(self, obj, method_name):
        if obj._proxy:
            self.func = getattr(obj._proxy, method_name)
#             print('direct')
        else:
            self.func = obj.con.call
            self.indirect = True
#             print('indirect !')
        self.obj = obj
        self.method_name = method_name
#         print(method_name)

    def __call__(self, *args, **kwargs):
        d = defer.Deferred()
        if 'timeout' in kwargs:
            timeout = kwargs['timeout'*1000]
        else:
            timeout = self.obj.timeout*1000
        if self.indirect:
            newargs = [self.obj.bus_name, self.obj.object_path,
                       self.obj.interface, self.method_name]
            if len(args) > 0:
                print(args)
                newargs.append(get_Gvariant(args))
            else:
                newargs.append(None)
            newargs += [None, 0, self.obj.timeout*1000,
                        None, self.result_indirect, d]
            print(newargs)
            self.func(*newargs)
            return d
        else:
            if len(args) > 0:
                sign = '('
                for arg in args:
                    sign = sign + guess_signature(arg)
                sign = sign + ')'
                args = list(args)
                args.insert(0, sign)
                args = tuple(args)
#             print(args)
            kwargs.update(
                {'result_handler': self.result,
                 'error_handler': self.error,
                 'user_data': d,
                 'timeout_msec': timeout})
#             print(kwargs)
            self.func(*args, **kwargs)
            return d

    def result(self, obj, result, d):
        if isinstance(result, Exception):
            self.error(obj, result, d)
        else:
            d.callback(result)

    def error(self, obj, error, d):
        d.errback(error)

    def result_indirect(self, obj, result, d):
        if isinstance(result, Exception):
            self.error(obj, result, d)
        else:
            r = self.obj.con.call_finish(result)
#             print('indirect_result :%s' % r)
            if len(r) > 0:
                d.callback(r[0])
            else:
                d.callback(None)


class DbusConnection(object):

    con = None
    errors = 0
    loop = None

    def __init__(self, bus_type=Gio.BusType.SESSION):
        self.bus_type = bus_type
        d = deferToThread(GObject.MainLoop)
        d.addCallback(self.loop_started)

    def connect_addr(self, addr):
        self.errors = 0
        os.environ['DBUS_SESSION_BUS_ADDRESS'] = addr
        return self.connect()

    def connect(self):
        if not self.loop:
            self.errors += 1
            if self.errors > 5:
                d = defer.fail(Exception('Unable to get Main loop'))
            else:
                d = task.deferLater(reactor, 1, self.connect)
            return d
        self.errors = 0
        d = defer.Deferred()
        self.con_deferred = d
        self.con = Gio.bus_get(self.bus_type, callback=self.connected)
        return d

    def loop_started(self, loop):
        self.loop = loop

    def connected(self, error, con):
        if isinstance(con, Exception):
            self.con_deferred.errback(con)
        else:
            try:
                self.con = Gio.bus_get_finish(con)
            except Exception as err:
                self.con_deferred.errback(err)
                return
            self.con_deferred.callback(self.con)

    def watch_process(self, process, func):
        def clbk(*res):
            if res[-1][0] == process:
                func(process, res[-2])
#             for r in res:
#                 print(res, process)
        if self.con:
            self.con.signal_subscribe(
                'org.freedesktop.DBus',
                'org.freedesktop.DBus',
                'NameOwnerChanged',
                None,
                None,
                0,
                clbk)
            return
        else:
            raise Exception('Not Connected to Dbus Session')


class ODbusProxy(object):
    '''
    Manage dbus proxy object in async manner

    Parameters
    ----------
    con: DBusConnection

    bus_name: string,  optional
        Name of the service to connect.
        default to org.freedesktop if not provided.

    object_path : string, optional
        Path of the object.
        If not provided, bus_name translated to path format is used.

    interface : string, optional
        Interface of the object
        Defaults to bus_name if not provided

    callback_fct : function, optional
        Function which receive events

    signal_subscriptions : list of g-signal, optional
        signals to subscribe to subscribe
        defaults to g-properties-changed

    timeout : int, optional
        Global timeout in seconds for method call
        Default to 5.0

    Returns
    -------
    ProxyObject
         Implements all the Interfaces exposed by the remote object.
         If the service does not support remote object owning, all methods
         are converted to low-level calls.
         All methods calls are asynchronous and returns a Deferred object.

    '''
    _proxy = None
    con = None

    def __init__(self, con,
                 bus_name='org.freedesktop',
                 object_path=None,
                 interface=None,
                 callback_fct=None,
                 signal_subscriptions=[['g-signal', 'properties']],
                 timeout=5):
        '''
        Constructor
        '''
        self.con = con
        if not object_path:
            object_path = "/" + bus_name.replace(".", "/")
        if not interface:
            interface = bus_name
        self.object_path = object_path
        self.bus_name = bus_name
        self.interface = interface
        self.timeout = timeout
        self.callback_fct = callback_fct
        self.signals = signal_subscriptions

    def get_proxy(self):
        d = defer.Deferred()
        self.proxy_deferred = d
#         print('proxy')
        Gio.DBusProxy.new(self.con, 0, None, self.bus_name, self.object_path,
                          self.interface, None, callback=self.got_proxy)
        return d

    def got_proxy(self, ignored, res):
        if isinstance(res, Exception):
            print('prox method not allowed for object: %s' % self.bus_name)
            self._proxy = None
            self.proxy_deferred.callback(None)
        else:
            self._proxy = Gio.DBusProxy.new_finish(res)
            if self.callback_fct:
                try:
                    for signal in self.signals:
                        self._proxy.connect(signal[0], self.event, signal[1])
                except Exception as err:
                    print('////////' + str(err))
            self.proxy_deferred.callback(self._proxy)

    def event(self, obj, tst, name, msg, *args):
        #         print('New Event: tst=%s ,name=%s, interface=%s,
        #         msg=%s, args=%s'
        #               % (tst, name, msg[0], msg[1], args))
        for signal in self.signals:
            if signal[1] is not None:
                self.callback_fct(args, msg)
            else:
                self.callback_fct(msg)

    def __getattr__(self, name):
        return Async_call_decorate(self, name)


def get_user_sessions():
    # try to obtain a user dbus session, works even without X11
    if os.getenv('DBUS_SESSION_BUS_ADDRESS') is None:
        daemons = []
        for proc in psutil.process_iter():
            if proc.username() == os.environ['USER']:
                if proc.name().startswith('dbus-daemon'):
                    lastaddr = ''
                    for bus in proc.connections('unix'):
                        if 'dbus' in bus.laddr:
                            addr = "unix:abstract=%s" \
                                % bus.laddr.split('@')[1]
                            if addr != lastaddr:
                                lastaddr = addr
                                daemons.append(addr)
        return daemons


def get_Gvariant(obj):
    if isinstance(obj, tuple):
        l = []
        for item in obj:
            l.append(get_Gvariant(item))
        return GLib.Variant.new_tuple(*l)
    if isinstance(obj, list):
        l = []
        for item in obj:
            l.append(get_Gvariant(item))
        v = GLib.Variant.new_array(
            GLib.VariantType.new(guess_signature(obj[0])), l)
        return v
    if isinstance(obj, dict):
        l = []
        key_type = GLib.VariantType.new(
            guess_signature(obj.keys()[0]))
        val_type = GLib.VariantType.new(
            guess_signature(obj[obj.keys()[0]]))
        for k, v in obj.items():
            l.append(
                GLib.Variant.new_dict_entry(
                    GLib.Variant(key_type, k), GLib.Variant(val_type, v)))
        return GLib.Variant.new_array(
            GLib.VariantType('{'+key_type+val_type+'}'), l)
    if isinstance(obj, int):
        if obj < 0:
            if obj < -2147483647:
                return GLib.Variant.new_int64(obj)
            else:
                return GLib.Variant.new_int32(obj)
        elif obj > 2147483647:
            return GLib.Variant.new_int64(obj)
        else:
            return GLib.Variant.new_int32(obj)
    if isinstance(obj, str):
        if GLib.Variant.is_object_path(obj):
            return GLib.Variant.new_object_path(obj)
        return GLib.Variant.new_string(obj)
    if isinstance(obj, bool):
        return GLib.Variant.new_boolean(obj)
    if isinstance(obj, float):
        return GLib.Variant.new_double(obj)


def guess_signature(obj):
    if isinstance(obj, list):
        return 'a' + guess_signature(obj[0])
    if isinstance(obj, dict):
        return '{' + guess_signature(obj.keys()[0]) +\
            guess_signature(obj[obj.keys()[0]])
    if isinstance(obj, int):
        if obj < 0:
            if obj < -2147483647:
                return 'x'
            else:
                return 'i'
        elif obj > 2147483647:
            return 'x'
        else:
            return 'i'
    if isinstance(obj, str):
        if GLib.Variant.is_object_path(obj):
            return 'o'
        else:
            return 's'
    if isinstance(obj, bool):
        return 'b'
    if isinstance(obj, float):
        return 'd'

if __name__ == '__main__':

    def test():
        con = DbusConnection()
        d = con.connect()
        d.addCallback(get_objects, con)
        d.addCallback(got_objects)

    def got_objects(objects):
        player, properties, tracklist = objects
        l = []
        for obj in objects:
            l .append(obj.get_proxy())
        d = defer.gatherResults(l)
        d.addCallback(
            lambda ignored: properties.Get(
                'org.mpris.MediaPlayer2.Player', 'PlaybackStatus'))
#         d = properties.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
        d.addCallback(show)
        d.addCallback(
            lambda ignored: player.Play())
        d.addCallback(show)
        d.addCallback(
            lambda ignored: properties.Get(
                'org.mpris.MediaPlayer2.TrackList', 'Tracks'))
        d.addCallback(show)
        d.addCallback(lambda tracks: tracklist.GetTracksMetadata(tracks))
        d.addCallback(show)
#         d.addCallback(lambda ignored: kuit())
        reactor.callLater(40,  # @UndefinedVariable
                          kuit)

    def show(msg):
        print('***********%s************' % msg)
        return msg

    def event(*args):
        print('event from %s: %s' % (args[0], args[1]))

#         print('!!!!!!!!!!!!!!!%s event !!!!!!!!!!!!' % arg)
    def kuit():
        log.err('Bye !')
        reactor.stop()  # @UndefinedVariable

    def get_objects(con, parent):

        player = ODbusProxy(
            con,
            bus_name='org.mpris.MediaPlayer2.vlc',
            object_path='/org/mpris/MediaPlayer2',
            interface='org.mpris.MediaPlayer2.Player',
            timeout=5)
        properties = ODbusProxy(
            con,
            bus_name='org.mpris.MediaPlayer2.vlc',
            object_path='/org/mpris/MediaPlayer2',
            interface='org.freedesktop.DBus.Properties',
            callback_fct=event,
            timeout=5)
        tracklist = ODbusProxy(
            con,
            bus_name='org.mpris.MediaPlayer2.vlc',
            object_path='/org/mpris/MediaPlayer2',
            interface='org.mpris.MediaPlayer2.TrackList',
            callback_fct=event,
            signal_subscriptions=[['g-signal', 'tracklist']],
            timeout=5)
        parent.watch_process('org.mpris.MediaPlayer2.vlc', event)
        return player, properties, tracklist
    reactor.callWhenRunning(  # @UndefinedVariable
        test)
    reactor.run()  # @UndefinedVariable
