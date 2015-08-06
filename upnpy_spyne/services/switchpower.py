'''
Created on 8 mai 2015

@author: babe
'''
from twisted.python import log
from upnpy_spyne.services import Service


class SwitchPower(Service):
    version = (1, 0)
    serviceType = "urn:schemas-upnp-org:service:SwitchPower:1"
    serviceId = "urn:schemas-upnp-org:serviceId:SwitchPower"
    serviceUrl = "SP"
#     frienlyName = "UpnP_Playlist"
    type = 'Light'
    upnp_type = 'upnp'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application'):
        super(SwitchPower, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.client = client
        self.client.event = self.upnp_event
        self.status = self.client.status

    def upnp_event(self, evt, var):
        if hasattr(self, 'parent'):
            log.err('%s Switch Power event: %s  ==> %s' % (
                                        self.parent.friendlyName, var, evt))
        setattr(self, var, evt)
