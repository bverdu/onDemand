# encoding: utf-8
'''
Created on 15 sept. 2015

@author: Bertrand Verdu
'''
from twisted.logger import Logger
from upnpy_spyne.services import Service


class FanOperatingMode(Service):
    '''
    classdocs
    '''
    version = (1, 0)
    serviceType = 'urn:schemas-upnp-org:service:HVAC_FanOperatingMode:1'
    serviceId = 'urn:schemas-upnp-org:serviceId:HVAC_FanOperatingMode'
    serviceUrl = 'fanmode'
    type = 'FanOperating'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application', system=False):
        '''
        Constructor
        '''
        super(FanOperatingMode, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.log = Logger()
        self.client = client
        self.client.UPNP_fan_event = self.upnp_event
        self.mode = 'ContinuousOn'
        self.fanstatus = 'Off'
        self.name = name

    def upnp_event(self, evt, var):
        self.log.debug('fan event: %s  ==> %s' % (var, evt))
        setattr(self, var, evt)
