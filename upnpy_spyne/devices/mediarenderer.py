'''
Created on 10 mai 2015

@author: Bertrand Verdu
'''

from upnpy_spyne.devices import Device
from upnpy_spyne.services.AVtransport import AVTransport
from upnpy_spyne.services import Service, get_event_catcher


class MediaRenderer(Device):

    def __init__(self, path, player, datadir, uuid=''):
        Device.__init__(self, path)
        self._description = None
        self.datadir = datadir
        self.player = player
        self.player.parent = self
        self.type = 'MediaRenderer'
        self.deviceType = 'urn:schemas-upnp-org:device:MediaRenderer:1'
        self.manufacturer = "upnpy"
        self.manufacturerURL = "http://github.com/bverdu/upnpy"
        self.manufacturerInfo = "coucou, c'est nous"
        self.modelDescription =\
            "an UPnP Media Renderer"
        self.modelName = "Snap_Media"
        self.version = (1, 0,)
        self.avtransport = AVTransport(
            datadir + 'xml/AVTransport1.xml', self.player)
        self.conmanager = Service(
            'Connection Manager',
            'urn:schemas-upnp-org:service:ConnectionManager:1',
            client=self.player,
            xml=datadir + 'xml/ConnectionManager1.xml')
        self.conmanager.upnp_event = get_event_catcher(self.conmanager)
        self.player.upnp_eventCM = self.conmanager.upnp_event
        self.rcontrol = Service(
            'Rendering Control',
            'urn:schemas-upnp-org:service:RenderingControl:1',
            client=self.player,
            xml=datadir + 'xml/RenderingControl1.xml')
        self.rcontrol.upnp_event = get_event_catcher(self.rcontrol)
        self.player.upnp_eventRCS = self.rcontrol.upnp_event
        self.services = [
            self.avtransport,
            self.conmanager,
            self.rcontrol]
        for service in self.services:
            service.parent = self
#         self.namespaces['dlna'] = 'urn:schemas-dlna-org:device-1-0'
#         self.extras['dlna:X_DLNADOC'] = 'DMS-1.50'
#     from tap import h
#     print(h.heap())

    def sendIR(self):
        raise NotImplementedError()
