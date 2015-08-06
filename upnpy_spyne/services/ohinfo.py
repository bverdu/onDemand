'''
Created on 22 janv. 2015

@author: babe
'''
from twisted.python import log
from upnpy_spyne.services import Service


class Info(Service):
    version = (1, 0)
    serviceType = "urn:av-openhome-org:service:Info:1"
    serviceId = "urn:av-openhome-org:serviceId:Info"
    serviceUrl = "Info"
    type = 'Info'
    upnp_type = 'oh'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application'):
        super(Info, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.client = client
        self.client.oh_eventINFO = self.upnp_event
        self.trackcount = self.client.trackcount
        self.detailscount = self.client.detailscount
        self.metatexcount = self.client.metatextcount
        self.uri = ''
        self.metadata = ''
        self.duration = 0
        self.bitrate = 0
        self.bitdepth = 0
        self.samplerate = 0
        self.lossless = False
        self.codecname = ''
        self.metatext = ''

    def upnp_event(self, evt, var):
#         print(evt)
        log.msg('info event: %s  ==> %s' % (var, evt))
        if var == 'trackcount':
            self.trackcount += 1
            self.detailscount = 0
            self.metatextcount = 0
        else:
            self.detailscount += 1
            setattr(self, var, evt)
