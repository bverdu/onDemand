#!/usr/local/bin/python2.7
# encoding: utf-8
'''
onDemand.GstreamerClient -- shortdesc

onDemand.GstreamerClient is a description

It defines classes_and_methods

@author:     user_name

@copyright:  2015 organization_name. All rights reserved.

@license:    license

@contact:    user_email
@deffield    updated: Updated
'''
from twisted.internet import gireactor
from twisted.internet.threads import deferToThread
from twisted.python import log

from gi.repository import GObject, Gst  # @UnresolvedImport


gireactor.install()

from twisted.internet import reactor


class Player(object):
    current_URI = ''
    _state = Gst.State.NULL
    upnp_state = 'STOPPED'
    oh_state = 'Stopped'
    loop = None
    ok = 0

    def __init__(self):
        Gst.init_check(None)
        self.player = Gst.ElementFactory.make("playbin", "onDemandPlayer")
        if not self.player:
            raise Exception('Gstreamer Playbin plugin not installed')
        self.bus = self.player.get_bus()
#         bus.add_watch(500, self.manager, self.loop)

    def loop_started(self, loop):
        self.loop = loop
        d = deferToThread(self.bus.add_watch,
                          *(500, self.manager, self.loop))
        return d

    def started(self, bus_id):
        self._bus_id = bus_id
        return bus_id

    def changed_state(self, new_gst_state, gst_pending_state):
        if new_gst_state != self._state:
            if new_gst_state == Gst.State.READY:
                return
            elif new_gst_state == Gst.State.PAUSED\
                    and gst_pending_state == Gst.State.VOID_PENDING:
                self._state = new_gst_state
                self.upnp_state = 'PAUSED_PLAYBACK'
                self.oh_state = 'Paused'
            elif new_gst_state == Gst.State.PLAYING\
                    and gst_pending_state == Gst.State.VOID_PENDING:
                self._state = new_gst_state
                self.upnp_state = 'PLAYING'
                self.oh_state = 'Playing'
            elif new_gst_state == Gst.State.NULL\
                    and gst_pending_state == Gst.State.VOID_PENDING:
                self._state = new_gst_state
                self.upnp_state = 'STOPPED'
                self.oh_state = 'Stopped'
            log.msg(self.upnp_state, level='debug')
            self.event_upnpAV(self.upnp_state, 'state')
            self.event_ohPLAYLIST(self.oh_state, 'state')

    def play(self):
        if self._state != Gst.State.PLAYING:
            #             log.err('Play')
            if not self.loop:
                d = deferToThread(GObject.MainLoop)
                d.addCallback(self.loop_started)
                d.addCallback(
                    lambda bus_id: self.player.set_state(Gst.State.PLAYING))
            else:
                self.player.set_state(Gst.State.PLAYING)
#             self._state = 'PLAYING'

    def stop(self):
        if self._state != Gst.State.NULL:
            #             log.err('Stop')
            self.player.set_state(Gst.State.NULL)
            self.loop.quit()
            self.changed_state(Gst.State.NULL, Gst.State.VOID_PENDING)

    def pause(self):
        if self._state != Gst.State.PAUSED:
            #             log.err('pause')
            self.player.set_state(Gst.State.PAUSED)
#             self._state = 'PAUSED'

    def set_position(self, ns):
        log.err('Seek ?')

        def result(res):
            log.err(res)
            if not res:
                log.err('Seek Failed: %s')
        event = Gst.Event.new_seek(
            1.0, Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
            Gst.SeekType.SET, ns,
            Gst.SeekType.NONE, 0)
        d = deferToThread(self.player.send_event,
                          event)
        d.addBoth(result)

    def open_uri(self, uri, md):
        def uri_checked(res, uri):
            if not res:
                d = deferToThread(Gst.filename_to_uri,
                                  uri)
                return d
            else:
                return uri

        def set_uri(uri):
            self.player.set_property('uri', uri)
            self.current_URI = uri

        d = deferToThread(Gst.uri_is_valid,
                          uri)
        d.addBoth(uri_checked, uri)
        d.addBoth(set_uri)

    def manager(self, bus, message, loop):
        if self.ok == 0:
            print(dir(message))
            self.ok += 1
        t = message.type
        if message.src == self.player:
            t = message.type
            if t == Gst.MessageType.STATE_CHANGED:
                s = message.parse_state_changed()
                self.changed_state(s[1], s[2])
            elif t == Gst.MessageType.EOS:
                log.err('EOS')
                self.changedstate(Gst.State.NULL, Gst.State.VOID_PENDING)
            return True
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            log.err("Error: %s: %s\n" % (err, debug))
            loop.quit()

        return True

    def event_upnpAV(self, evt, varname):
        log.err("upnpAV event: %s %s" % (varname, evt))

    def event_ohPLAYLIST(self, evt, varname):
        log.err("ohPLAYLIST event: %s %s" % (varname, evt))


if __name__ == '__main__':

    def kuit():
        log.err('Bye !')
        reactor.stop()  # @UndefinedVariable
    player = Player()
    reactor.callWhenRunning(  # @UndefinedVariable
        player.open_uri,
        *('file:/home/babe/Projets/eclipse/onDemand/test.avi', ''))
    reactor.callLater(1,  # @UndefinedVariable
                      player.play)
    reactor.callLater(5,  # @UndefinedVariable
                      player.pause)
    reactor.callLater(10,  # @UndefinedVariable
                      player.play)
    reactor.callLater(15,  # @UndefinedVariable
                      player.set_position,
                      80000000000)
    reactor.callLater(20,  # @UndefinedVariable
                      player.pause)
    reactor.callLater(25,  # @UndefinedVariable
                      player.stop)
    reactor.callLater(30,  # @UndefinedVariable
                      kuit)  # @UndefinedVariable
    reactor.run()  # @UndefinedVariable
