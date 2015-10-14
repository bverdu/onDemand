'''
Created on 22 janv. 2015

@author: Bertrand Verdu
'''
from twisted.application import internet
from onDemand.protocols.lirc import LircdFactory


class lircService(internet.UNIXClient):  # @UndefinedVariable
    def __init__(self, parent, addr, delay, direction='both', simul=False):
        self._player = parent.player
        lirc = LircdFactory(delay, simul)
        if direction in ('receiver', 'both'):
            lirc.addCallback('KEY_PLAYPAUSE'+'devinput',
                             self._player.playpause)
            lirc.addCallback('KEY_PLAY'+'devinput', self._player.play)
            lirc.addCallback('KEY_PAUSE'+'devinput', self._player.pause)
            lirc.addCallback('KEY_ESC'+'devinput', self._player.stop)
            lirc.addCallback('KEY_VOLUMEUP'+'devinput', self._player.volUp)
            lirc.addCallback('KEY_VOLUMEDOWN'+'devinput', self._player.volDown)
            lirc.addCallback('KEY_NEXTSONG'+'devinput', self._player.next)
            lirc.addCallback('KEY_PREVIOUSSONG'+'devinput',
                             self._player.previous)
        if direction in ('emitter', 'both'):
            parent.sendIR = lirc.send
        self.addr = addr
        internet.UNIXClient.__init__(self, addr, lirc)  # @UndefinedVariable
