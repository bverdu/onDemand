# encoding: utf-8
'''
Created on 19 août 2015

@author: Bertrand Verdu
'''
import importlib
from uuid import uuid4
from twisted.logger import Logger
from onDemand import config
from onDemand.utils import save_yaml

log = Logger()


# def get_subservices(conf=config):
#
#     endpoints = {}
#     clients = {}
#     services = []
#     webserver = None
#
#     for room, dic in conf.rooms.items():
#
#         for client in dic['clients']:
#
#             if client['type'] in conf.hmodules:
#
#                 hwopts = conf.hmodules[client['type']]['options']
#                 module_name = conf.hmodules[client['type']]['module']
#
#                 if client['type'] not in endpoints:
#
#                     t = getattr(
#                         importlib.import_module(
#                             'onDemand.plugins.' + module_name),
#                         'get_' + client['type'])
#                     d = {}
#                     d.update(hwopts if isinstance(hwopts, dict) else {})
#                     d.update(client['options'])
#                     d.update({'net_type': config.network})
#                     e, f = t(**d)
#                     if e:
#                         endpoints.update({client['type']: e})
#                 else:
#
#                     t = getattr(
#                         importlib.import_module(
#                             'onDemand.plugins.' + module_name),
#                         client['type'] + '_factory')
#                     d = client['options']
#                     d.update({'net_type': config.network})
#                     f = t(**d)
#                     endpoints[client['type']].connect(f)
#                 f.room = room
#
#                 if room not in clients:
#
#                     clients.update({room: {}})
#                 clients[room].update({client['name']: f})
#
#                 if client['service'] == 'MediaRenderer':
#
#                     for mt in conf.media_types:
#
#                         if mt == 'oh':
#
#                             from upnpy_spyne.devices.ohSource import Source
#                             device = Source(client['name'],
#                                             f,
#                                             conf.datadir)
#                         else:
#
#                             from upnpy_spyne.devices.mediarenderer\
#                                 import MediaRenderer
#                             device = MediaRenderer(
#                                 client['name'], f, conf.datadir)
#                 else:
#
#                     device = getattr(
#                         importlib.import_module(
#                             'upnpy_spyne.devices.' +
#                             client['service'].lower()),
#                         'MainDevice')(client['name'], f, conf.datadir)
#
#                 if config.network in ('lan', 'both'):
#
#                     from upnpy_spyne.upnp import UPnPService
#                     from upnpy_spyne.ssdp import SSDPServer
#                     upnp_server = UPnPService(device)
#                     services.append(upnp_server)
#                     ssdp_server = SSDPServer(device)  # SSDP
#                     services.append(ssdp_server)
#
#                 if config.network in ('cloud', 'both'):
#
#                     if not webserver:
#                         from onDemand.protocols.webserver import Local_server
#                         webserver = Local_server()
#                         services.append(webserver)
#                     from upnpy_spyne.xmpp import XmppService
#                     svc = []
#                     xmppService = XmppService(device,
#                                               user=conf.cloud_user,
#                                               secret=conf.cloud_secret,
#                                               web_server=webserver)
#                     svc.append(xmppService)
#                     for dev in device.devices:
#                         svc.append(XmppService(dev,
#                                                user=conf.cloud_user,
#                                                secret=conf.cloud_secret,
#                                                web_server=webserver))
#                     for xmpp in svc:
#                         services.append(xmpp)
#
#     return services


class get_subservices(object):

    def __init__(self, conf=config):

        self.endpoints = {}
        self.services = []
        self.conf = conf
        self.webserver = None
        updated = False

        if hasattr(conf, 'countries'):
            for country in conf.countries['countries']:
                if hasattr(conf, country):
                    for location in getattr(conf, country)['locations']:
                        if hasattr(conf, location):
                            for house in getattr(conf, location)['houses']:
                                if hasattr(conf, house):
                                    house_name = getattr(conf, house)['name']
                                    for room in getattr(conf, house)['rooms']:
                                        if hasattr(conf, room):
                                            room_name = getattr(
                                                conf, room)['name']
                                            for device in getattr(
                                                    conf, room)['devices']:
                                                if hasattr(conf, device):
                                                    dev = getattr(conf, device)
                                                    dev.update(
                                                        {'path': '/'.join((
                                                            country,
                                                            location,
                                                            house_name,
                                                            room_name,
                                                            dev['name']))})
                                                    self.get_subservice(
                                                        dev)
                                        else:
                                            setattr(conf,
                                                    room,
                                                    {'id': room,
                                                     'devices': [],
                                                     'name': 'Living Room'})
                                            updated = True
                                else:
                                    setattr(conf, house, {'id': house,
                                                          'rooms': [uuid4()],
                                                          'name': 'Home'})
                                    updated = True
                        else:
                            setattr(conf,
                                    location,
                                    {'houses': [uuid4()],
                                     'id': location,
                                     'name': 'Paris (France)'})
                            updated = True
                else:
                    setattr(conf, 'locations', {'locations': [uuid4()]})
                    updated = True
        if updated:
            save_yaml(conf.datadir, filename='test.yml')

    def __call__(self):
        return self.services

    def get_subservice(self, device, room='Living', house='Home',
                       location='FR/75000', country='France'):
        log.debug('%s' % device['path'])
        if device['type'] in self.conf.hmodules:
            hwopts = self.conf.hmodules[device['type']]['options']
            module_name = self.conf.hmodules[device['type']]['module']
            if device['type'] not in self.endpoints:
                t = getattr(
                    importlib.import_module(
                        'onDemand.plugins.' + module_name),
                    'get_' + device['type'])
                d = {}
                d.update(hwopts if isinstance(hwopts, dict) else {})
                d.update(device['options'])
                d.update({'net_type': self.conf.network})
                e, f = t(**d)
                if e:
                    self.endpoints.update({device['type']: e})
            else:
                t = getattr(
                    importlib.import_module(
                        'onDemand.plugins.' + module_name),
                    device['type'] + '_factory')
                d = device['options']
                d.update({'net_type': self.conf.network})
                f = t(**d)
                self.endpoints[device['type']].connect(f)
            f.room = room
            if device['service'] == 'MediaRenderer':

                for mt in self.conf.media_types:

                    if mt == 'oh':

                        from upnpy_spyne.devices.ohSource import Source
                        upnp_device = Source(device['path'],
                                             f,
                                             self.conf.datadir)
                    else:
                        from upnpy_spyne.devices.mediarenderer\
                            import MediaRenderer
                        upnp_device = MediaRenderer(
                            device['path'], f, self.conf.datadir)
            else:

                upnp_device = getattr(
                    importlib.import_module(
                        'upnpy_spyne.devices.' +
                        device['service'].lower()),
                    'MainDevice')(device['path'], f, self.conf.datadir)

            if config.network in ('lan', 'both'):

                from upnpy_spyne.upnp import UPnPService
                from upnpy_spyne.ssdp import SSDPServer
                upnp_server = UPnPService(upnp_device)
                self.services.append(upnp_server)
                ssdp_server = SSDPServer(upnp_device)  # SSDP
                self.services.append(ssdp_server)

            if config.network in ('cloud', 'both'):

                if not self.webserver:
                    from onDemand.protocols.webserver import Local_server
                    self.webserver = Local_server()
                    self.services.append(self.webserver)
                from upnpy_spyne.xmpp import XmppService
                svc = []
                xmppService = XmppService(upnp_device,
                                          user=self.conf.cloud_user,
                                          secret=self.conf.cloud_secret,
                                          web_server=self.webserver)
                svc.append(xmppService)
                for dev in upnp_device.devices:
                    svc.append(XmppService(dev,
                                           user=self.conf.cloud_user,
                                           secret=self.conf.cloud_secret,
                                           web_server=self.webserver))
                for xmpp in svc:
                    self.services.append(xmpp)


if __name__ == '__main__':

    import sys
    from twisted.logger import globalLogBeginner, textFileLogObserver
    from onDemand.utils import load_yaml

    observers = [textFileLogObserver(sys.stdout)]
    globalLogBeginner.beginLoggingTo(observers)

    load_yaml('/home/babe/Projets/eclipse/onDemand/data/', filename='test.yml')
    get_subservices()()
