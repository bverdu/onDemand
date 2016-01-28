# encoding: utf-8
'''
Created on 15 sept. 2015

@author: Bertrand Verdu
'''

from . import Device
from upnpy_spyne.services.hvac_user_operating_mode import UserOperatingMode
from upnpy_spyne.services.hvac_fan_operating_mode import FanOperatingMode
from upnpy_spyne.services.temperature_sensor import TemperatureSensor


class HvacSystem(Device):
    '''
    classdocs
    '''

    def __init__(self, path, render, datadir, uuid=''):
        super(HvacSystem, self).__init__(path, uuid)
        self._description = None
        self.datadir = datadir
        self.render = render
        self.render.parent = self
        self.type = 'HVAC_System'
        self.deviceType = 'urn:schemas-upnp-org:device:HVAC_System:1'
        self.manufacturer = "onDemand"
        self.manufacturerURL = "http://github.com/bverdu/upnpy"
        self.manufacturerInfo = "coucou, c'est nous"
        self.modelDescription =\
            "onDemand HVAC Device"
        self.modelName = "onDemand_HVAC"
        self.version = (1, 0,)
        UOM = UserOperatingMode(
            datadir + 'xml/HVAC_UserOperatingMode1.xml',
            self.render,
            name=self.name,
            system=True)
        FOM = FanOperatingMode(
            datadir + 'xml/HVAC_FanOperatingMode1.xml',
            self.render,
            name=self.name,
            system=True)
        TS = TemperatureSensor(
            datadir + 'xml/TemperatureSensor1.xml',
            self.render,
            name=self.name,
            system=True)
        self.services = [
            UOM,
            FOM,
            TS]
        for service in self.services:
            service.parent = self
        self.update()

    def update(self):
        self._description = None
        self.devices = self.render.upnp_devices
#         for device in self.devices:
#             device.parent = self
