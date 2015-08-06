'''
Created on 22 janv. 2015

@author: babe
'''
from twisted.python import log
from upnpy_spyne.services import Service


class AVTransport(Service):
    version = (1, 0)
    serviceType = "urn:schemas-upnp-org:service:AVTransport:1"
    serviceId = "urn:upnp-org:serviceId:AVTransport"
    event_schema = 'urn:schemas-upnp-org:metadata-1-0/AVT/'
    serviceUrl = "AVTransport"
    subscription_timeout_range = (None, None)
    type = 'UpnpAv'
    upnp_type = 'upnp'

    def __init__(self, xmlfile, client, name='Application'):
        super(AVTransport, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.client = client
        self.client.upnp_eventAV = self.upnp_event

    def upnp_event(self, var, evt):
        log.msg('UPNP EVENT val: %s evt:%s' % (var, evt))
        setattr(self, var, evt)
