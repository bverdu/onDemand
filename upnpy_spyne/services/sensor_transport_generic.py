# encoding: utf-8
'''
Created on 1 sept. 2015

@author: Bertrand Verdu
'''

from twisted.logger import Logger
from . import Service

log = Logger()


class SensorTransport(Service):
    version = (1, 0)
    serviceType = "urn:schemas-upnp-org:service:ConfigurationManagement:1"
    serviceId = "urn:schemas-upnp-org:service:ConfigurationManagement"
    serviceUrl = "STG"
#     frienlyName = "UpnP_Playlist"
    type = 'ConfigurationManagement'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application'):
        super(SensorTransport, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.client = client
        self.client.eventSTG = self.upnp_event

    def upnp_event(self, evt, var):
        log.msg('STG event: %s  ==> %s' % (var, evt))
        setattr(self, var, evt)
