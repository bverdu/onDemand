# encoding: utf-8
'''
Created on 15 sept. 2015

@author: Bertrand Verdu
'''
from twisted.logger import Logger
from upnpy_spyne.services import Service


class HouseStatus(Service):
    '''
    classdocs
    '''
    version = (1, 0)
    serviceType = 'urn:schemas-upnp-org:service:HouseStatus:1'
    serviceId = 'urn:schemas-upnp-org:serviceId:HouseStatus'
    serviceUrl = 'house'
    type = 'House'
    subscription_timeout_range = (None, None)

    def __init__(self, xmlfile, client, name='Application'):
        '''
        Constructor
        '''
        super(HouseStatus, self).__init__(
            self.type, self.serviceType, xml=xmlfile,
            client=client, appname=name)
        self.log = Logger()
        self.client = client
        self.client.houses.append(self)
        self.occupancystate = 'Indeterminate'
        self.activitylevel = 'Regular'
        self.dormancylevel = 'Regular'

    def upnp_event(self, evt, var):
        self.log.debug('away event: %s  ==> %s' % (var, evt))
        setattr(self, var, evt)
