'''
Created on 22 janv. 2015

@author: babe
'''
from twisted.python import log
from upnpy_spyne.services import Service


class Volume(Service):
    version = (1, 0)
    serviceType = "urn:av-openhome-org:service:Volume:1"
    serviceId = "urn:av-openhome-org:serviceId:Volume"
    serviceUrl = "Volume"
    type = 'Volume'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application'):
        super(Volume, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.client = client
        self.client.oh_eventVOLUME = self.upnp_event
        self.volumemax = self.client.max_volume
        self.volumeunity = 3
        self.volume = self.volumemax
        self.volumesteps = self.volumemax
        self.volumemillidbperstep = 600
        self.balancemax = 10
        self.balance = 0
        self.fademax = 10
        self.fade = 0
        self.mute = 0

    def upnp_event(self, evt, var):
        log.msg('volume event: %s  ==> %s' % (var, evt))
        setattr(self, var, evt)
