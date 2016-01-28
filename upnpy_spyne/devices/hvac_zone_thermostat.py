# encoding: utf-8
'''
Created on 15 sept. 2015

@author: Bertrand Verdu
'''

from . import Device
from upnpy_spyne.services.hvac_user_operating_mode import UserOperatingMode
from upnpy_spyne.services.hvac_fan_operating_mode import FanOperatingMode
from upnpy_spyne.services.temperature_sensor import TemperatureSensor
from upnpy_spyne.services.house_status import HouseStatus
from upnpy_spyne.services.temperature_set_point import TemperatureSetPoint
# from upnpy_spyne.services.control_valve import ControlValve


class ZoneThermostat(Device):
    '''
    classdocs
    '''

    def __init__(self, path, url, render, datadir, uuid=''):
        super(ZoneThermostat, self).__init__(path, uuid)
        self.deviceURL = url
        self._description = None
        self.datadir = datadir
        self.render = render
        self.render.parent = self
        self.type = 'HVAC_ZoneThermostat'
        self.deviceType = 'urn:schemas-upnp-org:device:HVAC_ZoneThermostat:1'
        self.manufacturer = "onDemand"
        self.manufacturerURL = "http://github.com/bverdu/upnpy"
        self.manufacturerInfo = "coucou, c'est nous"
        self.modelDescription =\
            "onDemand HVAC Zone thermostat"
        self.modelName = "onDemand_ZoneThermostat"
        self.version = (1, 0,)
        HUOM = UserOperatingMode(
            datadir + 'xml/HVAC_UserOperatingMode1.xml',
            self.render,
            name=self.name)
        FOM = FanOperatingMode(
            datadir + 'xml/HVAC_FanOperatingMode1.xml',
            self.render,
            name=self.name)
        TS = TemperatureSensor(
            datadir + 'xml/TemperatureSensor1.xml',
            self.render,
            name=self.name)
        HS = HouseStatus(datadir + 'xml/TemperatureSensor1.xml',
                         self.render, name=self.name)
        TSP = TemperatureSetPoint(datadir + 'xml/TemperatureSensor1.xml',
                                  self.render, name=self.name)
        self.services = [
            HUOM,
            FOM,
            TS,
            HS,
            TSP]
        for service in self.services:
            service.parent = self
