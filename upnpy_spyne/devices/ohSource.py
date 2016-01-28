'''
Created on 17 avr. 2015

@author: Bertrand Verdu
'''

from upnpy_spyne.devices import Device
from upnpy_spyne.services.ohplaylist import Playlist
from upnpy_spyne.services.ohproduct import Product
from upnpy_spyne.services.ohinfo import Info
from upnpy_spyne.services.ohtime import Time
from upnpy_spyne.services.ohvolume import Volume


class Source(Device):

    def __init__(self, path, player, datadir, uuid=''):
        Device.__init__(self, path, uuid)
        self._description = None
        self.datadir = datadir
        self.player = player
        self.player.parent = self
        self.type = 'Source'
        self.deviceType = 'urn:linn-co-uk:device:Source:1'
        self.manufacturer = "upnpy"
        self.manufacturerURL = "http://github.com/bverdu/upnpy"
        self.manufacturerInfo = "coucou, c'est nous"
        self.modelDescription =\
            "an OpenHome Media Renderer"
        self.modelName = "Snap_Media (OpenHome)"
        self.version = (1, 0,)
        self.playlist = Playlist(
            datadir + 'xml/playlist.xml', self.player, name=self.name)
        self.sources = [self.playlist]
        self.product = Product(
            datadir + 'xml/product.xml', self.player, name=self.name)
        self.info = Info(datadir + 'xml/info.xml', self.player, name=self.name)
        self.time = Time(datadir + 'xml/time.xml', self.player, name=self.name)
        self.volume = Volume(
            datadir + 'xml/volume.xml', self.player, name=self.name)
        self.services = [
            self.product,
            self.playlist,
            self.time,
            self.info,
            self.volume]
        for service in self.services:
            service.parent = self
#         self.namespaces['dlna'] = 'urn:schemas-dlna-org:device-1-0'
#         self.extras['dlna:X_DLNADOC'] = 'DMS-1.50'
#     from tap import h
#     print(h.heap())

    def sendIR(self):
        raise NotImplementedError()
