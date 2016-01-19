# encoding: utf-8
'''
Created on 17 janv. 2016

@author: Bertrand Verdu
'''
import uuid
import socket
from upnpy_spyne.devices import Device
from upnpy_spyne.services.binarysensor import BinarySensor


class MainDevice(Device):
    '''
    classdocs
    '''

    def __init__(self, path, player, datadir):
        super(MainDevice, self).__init__(path)
        self._description = None
        self.datadir = datadir
        self.player = player
        self.type = 'UpnP'
        self.deviceType = 'urn:lazytech-io:device:Demo:1'
        self.manufacturer = "Lazytech"
        self.manufacturerURL = "https://lazytech.io"
        self.manufacturerInfo = "Control Everything, from EveryWhere"
        self.modelDescription =\
            "onDemand binary sensor"
        self.modelName = "Sensors Demo"
        self.version = (1, 0,)
        self.uuid = str(
            uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname() + path))
        self.sensor = BinarySensor(
            datadir + 'xml/binarysensor.xml', self.player, name=self.name)
        self.sensor.parent = self
        self.services = [self.sensor]
