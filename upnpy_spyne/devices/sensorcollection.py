# encoding: utf-8
'''
Created on 31 mai 2016

@author: Bertrand Verdu
'''
from upnpy_spyne.devices import Device
from upnpy_spyne.services import Service


class MainDevice(Device):
    '''
    classdocs
    '''

    def __init__(self, path, plugin, uuid=''):
        super(MainDevice, self).__init__(path, uuid)
        self.dynamic = True
        self.initialized = False
        self.parent = None
        self._description = None
        self.type = 'SensorCollection'
        self.deviceType = 'urn:lazytech-io:device:SensorCollection:1'
        self.manufacturer = "Lazytech"
        self.manufacturerURL = "https://github.com/lazytech-org"
        self.manufacturerInfo = "Control Everything, From EveryWhere"
        self.modelDescription =\
            "IoT sensors and Actuators collection proxy"
        self.modelName = "IoT SensorCollection (Lazytech)"
        self.version = (1, 0,)
        if plugin:
            self.plugin = plugin
            self.plugin.parent = self
            self.controller = Service('SensorProxy',
                                      "urn:lazytech-io:service:SensorProxy:1",
                                      client=self.plugin,
                                      dynamic=True)
            self.controller.url = 'sb'
            self.controller.serviceId = "urn:lazytech-io:serviceId:SensorProxy"
            self.services = [self.controller]
            for service in self.services:
                service.parent = self
            if plugin.initialized:
                self.generate_service()
            else:
                plugin.update_config = self.generate_service

    def generate_service(self):
        if hasattr(self.plugin, 'state_variables'):
            for var in self.plugin.state_variables:
                self.controller.append_state_variable(var)
        if hasattr(self.plugin, 'actions'):
            for k, v in self.plugin.actions.iteritems():
                self.controller.append_action({k: v})
        self.controller.make_app()
        self._description = None
        self.controller._description = None
        self.initialized = True
        if self.parent is not None:
            self.parent.description = None
            self.parent.add_device(self)
