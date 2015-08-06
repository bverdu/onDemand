'''
Created on 22 janv. 2015

@author: babe
'''
from twisted.python import log
from upnpy_spyne.services import Service
from templates.renderingControl import RenderingControlService


class RenderingControl(RenderingControlService):
    def __init__(self, player):
        self.player = player
        self.event_schema = 'urn:schemas-upnp-org:metadata-1-0/RCS/'
        player.upnp_eventRCS = self.upnp_event
        RenderingControlService.__init__(self)

    def upnp_event(self, var, evt):
        setattr(self, var, evt)

    @register_action('GetVolume')
    def get_volume(self, instanceID, channel):
        log.msg('GetVolume from RCS', loglevel='debug')
        return self.player.get_volume()

    @register_action('SetVolume')
    def set_volume(self, instanceID, channel, volume=0):
        log.msg('SetVolume from RCS', loglevel='debug')
        self.player.set_volume(channel, volume)

    @register_action('GetVolumeDBRange')
    def get_volumeDB_range(self, instanceID, channel):
        log.msg('GetVolumeDBRange from RCS', loglevel='debug')
        return({'MinValue': 53, 'MaxValue': 160})

    @register_action('GetVolumeDB')
    def get_volumeDB(self, instanceID, channel):
        log.msg('GetVolumeDB from RCS', loglevel='debug')
        return(75)
