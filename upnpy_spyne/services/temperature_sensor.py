# encoding: utf-8
'''
Created on 15 sept. 2015

@author: Bertrand Verdu
'''
from twisted.logger import Logger
from upnpy_spyne.services import Service


class TemperatureSensor(Service):
    '''
    classdocs
    '''
    version = (1, 0)
    serviceType = 'urn:schemas-upnp-org:service:TemperatureSensor:1'
    serviceId = 'urn:schemas-upnp-org:serviceId:TemperatureSensor'
    serviceUrl = 'temp'
    type = 'Temperature'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application', system=False):
        '''
        Constructor
        '''
        super(TemperatureSensor, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.log = Logger()
        self.client = client
        if system:
            self.application = 'Outdoor'
        else:
            self.application = 'Room'
        self.client.UPNP_Temp_event = self.upnp_event
        self.currenttemperature = 2000
        self.name = name

    def upnp_event(self, evt, var):
        self.log.debug('temp event: %s  ==> %s' % (var, evt))
        setattr(self, var, evt)
