# PyUPnP - Simple Python UPnP device library built in Twisted
# Copyright (C) 2013  Dean Gardiner <gardiner91@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lxml import etree as et
from upnpy_spyne.utils import make_element, get_version
from twisted.python import log


class Device(object):
    __slots__ = ['deviceType',
                 'friendlyName',
                 'manufacturer',
                 'manufacturerURL',
                 'modelDescription',
                 'modelName',
                 'version',
                 'uuid',
                 'datadir',
                 'devices',
                 'namespaces',
                 'extras',
                 'serialNumber',
                 'UPC',
                 'server',
                 '__dict__']
    version = (1, 0)
    parent = None
    # Description
    deviceURL = ''
    deviceType = None
    manufacturer = "upnpy"
    manufacturerURL = "http://github.com/bverdu/upnpy"
    friendlyName = "UPnPDev"
    modelDescription = "upnpy-lib"
    modelName = "upnpy"
    modelNumber = get_version()
    modelURL = "http://github.com/bverdu/upnpy"
    serialNumber = None
    UPC = None
    namespaces = {}

    _description = None

    # SSDP
    server = "Linux/x86_64 UPnP/1.0 upnpy/0.9"

    def __init__(self, path, uuid):
        self.UResource = None
        self.extras = {}
        # Description
        n = path.split('/')
        self.friendlyName = self.name = n[-1]
        if len(n) > 1:
            #             self.namespaces.update(
            #                 {'v': 'urn:schemas-ondemand-org:device-1-0'})
            self.extras.update({'X_location': '/'.join(n[:-1])})
        self.configID = 0
        if uuid == '':
            import uuid
            import socket
            self.uuid = str(
                uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname() + path))
        else:
            self.uuid = uuid

        # SSDP
        self.bootID = None
        self.location = None
        self.weburl = None

        #: :type: list of UPnP_Service
        self.services = []

        #: :type list of embedded Devices
        self.devices = []

        #: :type: list of DeviceIcon
        self.icons = []

        self.namespaces.update({
            '': 'urn:schemas-upnp-org:device-1-0'
        })

    def getLocation(self, address, desc=True):
        if '@' in self.location:
            return self.location
        if desc:
            return self.location % address + '/' + self.uuid + '/desc'
        else:
            return self.location % address + '/' + self.uuid

    def getweburl(self, address):
        return self.weburl % address

    def get_UDN(self):
        if self.uuid is None:
            return None
        return 'uuid:%s' % self.uuid
    UDN = property(get_UDN)

    def dump(self):
        log.msg("xml tree dumped")
#         root = et.Element('root', attrib={
#             'configId': str(self.configID)
#         })
        root = et.Element('root', {'encoding': 'utf-8', 'standalone': 'yes'})
        for prefix, namespace in self.namespaces.iteritems():
            if prefix == '':
                prefix = 'xmlns'
            else:
                prefix = 'xmlns:' + prefix
            root.attrib[prefix] = namespace

        # specVersion
        specVersion = et.Element('specVersion')
        specVersion.append(make_element('major', str(self.version[0])))
        specVersion.append(make_element('minor', str(self.version[1])))
        root.append(specVersion)

        root.append(self.dump_device())
        return root

    def dump_device(self):
        device = et.Element('device')

        for attr_name in [
            'deviceType',
            'friendlyName',
            'manufacturer',
            'manufacturerURL',
            'modelDescription',
            'modelName',
            'modelNumber',
            'modelURL',
            'serialNumber',
            'UDN'
        ]:
            if hasattr(self, attr_name):
                val = getattr(self, attr_name)
                if val is not None:
                    device.append(make_element(attr_name, val))

        for name, val in self.extras.iteritems():
            device.append(make_element(name, val))

        # icon List
        iconList = et.Element('iconList')
        for icon in self.icons:
            iconList.append(icon.dump())
        device.append(iconList)

        # service List
        serviceList = et.Element('serviceList')
        for service in self.services:
            _service = et.Element('service')
            _service.append(make_element('serviceType', service.serviceType))
            _service.append(make_element('serviceId', service.serviceId))
            _service.append(make_element(
                            'controlURL',
                            '/' + self.uuid + '/' +
                            service.serviceUrl + '/control'))
            _service.append(make_element(
                            'eventSubURL',
                            '/' + self.uuid + '/' +
                            service.serviceUrl + '/event'))
            _service.append(make_element('SCPDURL', '/' + self.uuid + '/' +
                                         service.serviceUrl))
            serviceList.append(_service)
        device.append(serviceList)

        # device List
        if len(self.devices) > 0:
            deviceList = et.Element('deviceList')
            for device_ in self.devices:
                _device = et.Element('device')
                _device.append(make_element('rootType', device_.deviceType))
                _spec_version = et.Element('specVersion')
                _spec_version.append(
                    make_element('major', str(device_.version[0])))
                _spec_version.append(
                    make_element('minor', str(device_.version[1])))
                _device.append(_spec_version)
                _device.append(make_element(
                    'baseURL',
                    '/' + device_.deviceUrl))
            deviceList.append(_device)
            device.append(deviceList)

        return device

    def dumps(self, force=False):
        if self._description is None or force:
            #             log.err('generate xml')
            self._description = '<?xml version="1.0"?>' + \
                et.tostring(self.dump())
        return self._description


class DeviceIcon:

    def __init__(self, mimetype, width, height, depth, url):
        self.mimetype = mimetype
        self.width = width
        self.height = height
        self.depth = depth
        self.url = url

    def dump(self):
        icon = et.Element('icon')
        icon.append(make_element('mimetype', self.mimetype))
        icon.append(make_element('width', str(self.width)))
        icon.append(make_element('height', str(self.height)))
        icon.append(make_element('depth', str(self.depth)))
        icon.append(make_element('url', self.url))
        return icon
