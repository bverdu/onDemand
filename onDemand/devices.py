# encoding: utf-8
'''
Created on 2 mars 2016

@author: Bertrand Verdu
'''


class Device(object):

    __slots__ = ('datadir', 'plugin', 'deviceType',
                 'manufacturer', 'manufacturerURL', 'manufacturerInfo',
                 'modelDescription', 'modelName', 'version', '_services')

    def __init__(self):
        self.deviceType = 'urn:schemas-upnp-org:device:Basic:1'
        self.manufacturer = "LazyTech"
        self.manufacturerURL = "https://lazytech.io"
        self.manufacturerInfo = "Control Everything, from Everywhere.."
        self.modelDescription =\
            "onDemand basic device"
        self.modelName = "basic"
        self.version = (1, 0,)
        self._services = []


class Source(Device):

    def __init__(self):
        super(Source, self).__init__()
        self.deviceType = 'urn:linn-co-uk:device:Source:1'
        self.modelDescription =\
            "an OpenHome Media Renderer"
        self.modelName = "OpenHome Media Renderer"
        self._services = ['Product', 'Playlist', 'Time', 'Info', 'Volume']


class BinaryLight(Device):

    def __init__(self):
        super(BinaryLight, self).__init__()
        self.deviceType = 'urn:schemas-upnp-org:device:BinaryLight:1'
        self.modelDescription = "Light switch"
        self.modelName = "UpnP Binary Light"
        self._services = ['SwitchPower']


class BinarySensor(Device):

    def __init__(self):
        super(BinarySensor, self).__init__()
        self.deviceType = 'urn:lazytech-io:device:BinarySensor:1'
        self.modelDescription = "Binary sensor (On/Off, proximity...)"
        self.modelName = "Lazytech Binary Sensor"
        self._services = ['BinarySensor']


class HVAC_System(Device):

    def __init__(self):
        super(HVAC_System, self).__init__()
        self.deviceType = 'urn:schemas-upnp-org:device:HVAC_System:1'
        self.modelDescription = "HVAC System"
        self.modelName = "UpnP HVAC System"
        self._services = ['UserOperatingMode', 'FanOperatingMode',
                          'TemperatureSensor']


class HVAC_ZoneThermostat(Device):

    def __init__(self):
        super(HVAC_ZoneThermostat, self).__init__()
        self.deviceType = 'urn:schemas-upnp-org:device:HVAC_ZoneThermostat:1'
        self.modelDescription = "HVAC Zone thermostat"
        self.modelName = "UpnP ZoneThermostat"
        self._services = ['UserOperatingMode', 'FanOperatingMode',
                          'TemperatureSensor', 'HouseStatus',
                          'TemperatureSetPoint']


class DimmableLight(Device):

    def __init__(self):
        super(DimmableLight, self).__init__()
        self.deviceType = 'urn:schemas-upnp-org:device:DimmableLight:1'
        self.modelDescription = "Light dimmer"
        self.modelName = "UpnP Dimmable Light"
        self._services = ['SwitchPower', 'Dimming']


class ColorLight(Device):

    def __init__(self):
        super(DimmableLight, self).__init__()
        self.deviceType = 'urn:lazytech-io:device:ColorLight:1'
        self.modelDescription = "Color Light control"
        self.modelName = "Lazytech Color Light"
        self._services = ['SwitchPower', 'Dimming', 'Color']


class MediaRenderer(Device):

    def __init__(self):
        super(MediaRenderer, self).__init__()
        self.deviceType = 'urn:schemas-upnp-org:device:MediaRenderer:1'
        self.modelDescription = "Media Renderer"
        self.modelName = "UpnP MediaRenderer"
        self._services = ['AVTransport', 'ConnectionManager',
                          'RenderingControl']


class MediaServer(Device):

    def __init__(self):
        super(MediaServer, self).__init__()
        self.deviceType = 'urn:schemas-upnp-org:device:MediaServer:1'
        self.modelDescription = "Media Server"
        self.modelName = "UpnP MediaServer"
        self._services = ['ContentDirectory', 'ConnectionManager',
                          'AVTransport']


class SensorManagement(Device):

    def __init__(self):
        super(SensorManagement, self).__init__()
        self.deviceType = 'urn:schemas-upnp-org:device:SensorManagement:1'
        self.modelDescription = "Sensors Manager"
        self.modelName = "UpnP Sensor Management"
        self._services = ['SensorTransportGeneric', 'ConfigurationManagement',
                          'DataStore', 'DeviceProtection']


class SensorProxy(Device):

    def __init__(self):
        super(SensorProxy, self).__init__()
        self.deviceType = 'urn:lazytech-io:device:SensorProxy:1'
        self.modelDescription = "Sensor proxy to 6lowpan, BLE, Zbee nodes"
        self.modelName = "Lazytech Sensor Proxy"
        self._services = ['SensorDirectory', 'SensorControl']


class SystemSettings(Device):

    def __init__(self):
        super(SystemSettings, self).__init__()
        self.deviceType = 'urn:lazytech-io:device:SystemSettings:1'
        self.modelDescription = "System control"
        self.modelName = "Lazytech System Settings"
        self._services = ['SystemSecurity', 'SystemConnectivity',
                          'SystemPlugins', 'SystemServices']
