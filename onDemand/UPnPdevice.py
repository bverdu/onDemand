'''
Created on 22 janv. 2015

@author: babe
'''
import uuid
import socket
from upnpy.device import Device
from upnpy.services.conManager import ConnectionManager
from upnpy.services.AVtransport import AVTransport
from upnpy.services.renderingControl import RenderingControl


class MainDevice(Device):
    '''
    classdocs
    '''
    def __init__(self, name, player, datadir):
        Device.__init__(self)
        self.datadir = datadir
        self.player = player
        self.type = 'UpnpAv'
        self.deviceType = 'urn:schemas-upnp-org:device:MediaRenderer:1'
        self.friendlyName = name
        self.manufacturer = "upnpy"
        self.manufacturerURL = "http://github.com/bverdu/upnpy"
        self.manufacturerInfo = "coucou, c'est nous"
        self.modelDescription =\
            "an UPnP renderer controlling mpd"
        self.modelName = "mpdRenderer"
        self.version = (1, 0,)
        self.uuid = str(
            uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname()+name))
        self.datadir = "/usr/share/pyRenderer/"
        self.connectionManager = ConnectionManager(player)
        self.avtransport = AVTransport(self)
        self.renderingcontrol = RenderingControl(player)
        self.services = [
            self.connectionManager,
            self.avtransport,
            self.renderingcontrol]
        for service in self.services:
            service.parent = self
        self.namespaces['dlna'] = 'urn:schemas-dlna-org:device-1-0'
        self.extras['dlna:X_DLNADOC'] = 'DMS-1.50'
#     from tap import h
#     print(h.heap())

    def sendIR(self):
        raise NotImplementedError()
