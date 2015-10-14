# -*- coding: utf-8 -*-
'''
Created on 22 janv. 2015

@author: Bertrand Verdu
'''
from twisted.python import log
from upnpy_spyne.services import Service


class Playlist(Service):
    version = (1, 0)
    serviceType = "urn:av-openhome-org:service:Playlist:1"
    serviceId = "urn:av-openhome-org:serviceId:Playlist"
    serviceUrl = "PL"
#     frienlyName = "UpnP_Playlist"
    type = 'Playlist'
    upnp_type = 'oh'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application'):
        super(Playlist, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.client = client
        self.client.oh_eventPLAYLIST = self.upnp_event
        self.transportstate = 'Stopped'
        self.repeat = self.client.repeat
        self.shuffle = self.client.shuffle
        self.id = self.client.songid
        self.idarray = self.client.idArray
        self.tracksmax = self.client.tracksmax
        self.protocolinfo = self.client.mtlist

    def upnp_event(self, evt, var):
        log.msg('playlist event: %s  ==> %s' % (var, evt))
        setattr(self, var, evt)
