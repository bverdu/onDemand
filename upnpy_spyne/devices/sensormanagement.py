# encoding: utf-8
'''
Created on 1 sept. 2015

@author: Bertrand Verdu
'''

from . import Device
from upnpy_spyne.services.configuration_management import\
    ConfigurationManagement
from upnpy_spyne.services.sensor_transport_generic import SensorTransport


class SensorManagement(Device):
    '''
    classdocs
    '''

    def __init__(self, path, render, datadir, uuid=''):
        super(SensorManagement, self).__init__(path, uuid)
        self._description = None
        self.datadir = datadir
        self.render = render
        self.render.parent = self
        self.type = 'SensorManagement'
        self.deviceType = 'urn:schemas-upnp-org:device:SensorManagement:1'
        self.manufacturer = "upnpy"
        self.manufacturerURL = "http://github.com/bverdu/upnpy"
        self.manufacturerInfo = "coucou, c'est nous"
        self.modelDescription =\
            "onDemand IOT Management Device"
        self.modelName = "onDemand_IOT"
        self.version = (1, 0,)
        self.CFG = ConfigurationManagement(
            datadir + 'xml/configurationmanagement.xml',
            self.render,
            name=self.name)
        self.STG = SensorTransport(
            datadir + 'xml/sensor_transport_generic.xml',
            self.render,
            name=self.name)
        self.services = [
            self.CFG,
            self.STG]
        for service in self.services:
            service.parent = self
