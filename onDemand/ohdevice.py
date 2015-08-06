'''
Created on 22 janv. 2015

@author: babe
'''
import uuid
import socket
from collections import OrderedDict
from twisted.python import log
from upnpy_spyne.device import Device
from upnpy_spyne.services.ohplaylist import Playlist
from upnpy_spyne.services.ohproduct import Product
from upnpy_spyne.services.ohinfo import Info
from upnpy_spyne.services.ohtime import Time
from upnpy_spyne.services.ohvolume import Volume
from upnpy_spyne.utils import get_default_v4_address, dict2xml


class Source(Device):
    sources = []
    sourcexml = ''
    standby = False
    type = 'Source'
    manufacturer = "upnpy"
    manufacturerURL = "http://github.com/bverdu/upnpy"
    manufacturerInfo = "coucou, c'est nous"
    modelName = "mpdRenderer (OpenHome)"
    deviceType = 'urn:linn-co-uk:device:Source:1'
    modelDescription = "an OpenHome renderer controlling mpd"

    def __init__(
            self, name, clients, datadir, room, sources=[], active_source=''):
        super(Source, self).__init__(self)
        self.productroom = room
        self.datadir = datadir
        self.client = clients[0]
        self.friendlyName = name
        self.version = (1, 0,)
        self.uuid = str(
            uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname()+name))
        self.playlist = Playlist(datadir + 'xml/playlist.xml', self)
        self.product = Product(
            datadir + 'xml/product.xml', 'Salon', [self.playlist], 0, self)
        self.info = Info(datadir + 'xml/info.xml', self.player)
        self.time = Time(datadir + 'xml/time.xml', self)
        self.volume = Volume(datadir + 'xml/volume.xml', self)
        self.services = [
            self.product,
            self.playlist,
            self.time,
            self.info,
            self.volume]
        for service in self.services:
            service.parent = self
        for source in sources:
            self.sources.append(OrderedDict(
                sorted({'Name': room + source.type + '0',
                        'Type': source.type,
                        'Visible': True}. items(), key=lambda t: t[0])))
#         self.sources = [OrderedDict(
#                         sorted(
#                             {'Name': room + active_source.type + '0',
#                              'Type': active_source.type,
#                              'Visible': True}. items(), key=lambda t: t[0])),
#                         OrderedDict(
#                         sorted(
#                             {'Name': room + self.parent.type + '0',
#                              'Type': self.parent.type,
#                              'Visible': True}. items(), key=lambda t: t[0]))]
        self.sourcexml = dict2xml(
            {'SourceList': [{'Source': n} for n in self.sources]})
#         self.namespaces['dlna'] = 'urn:schemas-dlna-org:device-1-0'
#         self.extras['dlna:X_DLNADOC'] = 'DMS-1.50'
#     from tap import h
#     print(h.heap())

    def wait_connection(self):
        try:
            addr = self.getLocation(get_default_v4_address())
            setattr(
                self, 'manufacturerimageurl', addr + '/pictures/icon.png')
            self.oh_product_event(
                'manufacturerimageurl', self.manufacturerimageurl)
            setattr(self,
                    'modelimageurl',
                    ''.join((addr, '/pictures/', self.modelname, '.png')))
            self.oh_product_event('modelimageurl', self.modelimageurl)
        except:
            reactor.callLater(1, self.wait_connection)  # @UndefinedVariable

    def add_source(self, source):
        self.sources.append(OrderedDict(
            sorted({'Name': self.productroom + source.type + '0',
                    'Type': source.type,
                    'Visible': True}. items(), key=lambda t: t[0])))
        self.oh_product_event('sources', self.sources)
        self.sourcexml = dict2xml(
            {'SourceList': [{'Source': n} for n in self.sources]})
        self.oh_product_event('sourcexml', self.sourcexml)

    def sendIR(self):
        raise NotImplementedError()

    def oh_product_event(self, var, evt):
        pass

    '''
    UPnP functions (used by OH product service)
    '''
    def manufacturer(self, ignored):
        log.err('Manufacturer from Product')
        return (self.manufacturer, self.manufacturerInfo, self.manufacturerURL,
                ''.join((
                    self.getLocation(get_default_v4_address()),
                    '/pictures/icon.png')),)

    def model(self, ignored):
        log.err('Model from Product')
        return (self.modelName, self.modelDescription, self.manufacturerURL,
                ''.join((self.getLocation(get_default_v4_address()),
                         '/pictures/', self.modelName, '.png',)))

    def product(self, ignored):
        log.err('Product from Product')
        return (self.productroom, self.modelName, self.modelDescription,)

    def standby(self, ignored):
        log.err('Standby from Product')
        return self.standby

    def set_standby(self, val=None, upnp_type='oh'):
        log.err('SetStandby from Product')
        if val is None:
            return self.standby
        raise NotImplementedError()

    def source_count(self, ignored):
        log.err('SourceCount from Product')
        return len(self.sources)

    def source_xml(self, ignored):
        log.err('SourceXml from Product')
        return dict2xml({'SourceList': [{'Source': n} for n in self.sources]})

    def source_index(self, ignored):
        log.err('SourceIndex from Product')
        return self.sourceindex

    def set_source_index(self, idx=None, upnp_type='oh'):
        log.err('SetSourceIndex from Product')
        if idx is None:
            return self.sourceindex
        else:
            try:
                self.sourceindex = int(idx)
                self.oh_product_event('sourceindex', self.sourceindex)
            except:
                for i, source in enumerate(self.sources.keys()):
                    if source['Name'] == idx:
                        self.sourceindex = i
                        self.oh_product_event('sourceindex', self.sourceindex)
                        return
                    log.err('Unknown Source: %s' % idx)

    def set_source_index_by_name(self, value, ignored):
        log.err('SetSourceIndexByName from Product')
        return self.set_source_index(value)

    def source(self, idx, ignored):
        idx = int(idx)
        return (self._sources[idx].friendlyName, self.sources[idx]['Type'],
                self.sources[idx]['Visible'], self.sources[idx]['Name'],)

    def attributes(self, ignored):
        return self.attributes

    def source_xml_change_count(self, ignored):
        raise NotImplementedError()
