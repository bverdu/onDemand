'''
Created on 17 avr. 2015

@author: babe
'''
import importlib

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from twisted.application import service
from utils import load_yaml


import config


def makeService(args):
    '''
    Create and launch main service
    '''
#     imports = '''
# from onDemand.%s import %s
# player = %s('%s', %d)
# '''
    endpoints = {}
    clients = {}
    mainService = service.MultiService()
#     load_config(args['datadir'])
    load_yaml(args['datadir'])
    for room, dic in config.rooms.items():
        for client in dic['clients']:
            if client['type'] in config.hmodules:
                hwopts = config.hmodules[client['type']]['options']
                module_name = config.hmodules[client['type']]['module']
                if client['type'] not in endpoints:
                    t = getattr(
                        importlib.import_module(
                            'onDemand.protocols.'+module_name),
                        'get_' + client['type'])
                    d = {}
                    d.update(hwopts if isinstance(hwopts, dict) else {})
                    d.update(client['options'])
                    e, f = t(**d)
                    if e:
                        endpoints.update({client['type']: e})
                else:
                    t = getattr(
                        importlib.import_module(
                            'onDemand.protocols.'+module_name),
                        client['type'] + '_factory')
                    f = t(**client['options'])
                    endpoints[client['type']].connect(f)
                f.room = room
                if room not in clients:
                    clients.update({room: {}})
                clients[room].update({client['name']: f})
                if client['service'] == 'MediaRenderer':
                    for mt in config.media_types:
                        if mt == 'oh':
                            from upnpy_spyne.devices.ohSource import Source
                            device = Source(client['name'], f, args['datadir'])
                        else:
                            from upnpy_spyne.devices.mediarenderer\
                                import MediaRenderer
                            device = MediaRenderer(
                                client['name'], f, args['datadir'])
                else:
                    device = getattr(
                        importlib.import_module(
                            'upnpy_spyne.devices.'+client['service'].lower()),
                        'MainDevice')(client['name'], f, args['datadir'])
                if config.network in ('lan', 'both'):
                    from upnpy_spyne.upnp import UPnPService
                    from upnpy_spyne.ssdp import SSDPServer
                    upnp_server = UPnPService(device)
                    mainService.services.append(upnp_server)
                    mainService.register_art_url = upnp_server.register_art_url
                    upnp_server.parent = mainService
                    ssdp_server = SSDPServer(device)  # SSDP
                    mainService.services.append(ssdp_server)
                    ssdp_server.parent = mainService
                if config.network in ('cloud', 'both'):
                    from spyne_plus.server.twisted.xmpp import XmppService
                    xmppService = XmppService(device, user=config.cloud_user)
                    mainService.services.append(xmppService)
                    xmppService.parent = mainService
    return mainService

#     # Take an aspirin...
#     if config.client is not None:
#         player = getattr(
#             importlib.import_module('onDemand.'+config.client.split()[0]),
#             config.client.split()[0].capitalize())(
#                 **{opt.split('=')[0].strip(): opt.split('=')[1].strip()
#                     for opt in config.client_opts.split(',')})
#         mainService.services.append(player)
#         player.parent = mainService
#     if config.protocol == 'upnp':
#         from onDemand.UPnPdevice import MainDevice
#         device = MainDevice(args["name"], player, args['datadir'])
#     elif config.protocol == 'oh':
#         from onDemand.ohmediarenderer import Source
#         device = Source(args["name"], player, args['datadir'])
#     elif config.protocol == 'all':
#         from onDemand.UPnPdevice import MainDevice  # @Reimport
#         device = MainDevice(args["name"], player, args['datadir'])
#         from onDemand.ohmediarenderer import Source  # @Reimport
#         second_device = Source(args["name"], player, args['datadir'])
#         second_device.datadir = args['datadir']
#         second_upnp_server = UPnPService(second_device)  # UPnP
#         mainService.services.append(second_upnp_server)
#         second_upnp_server.parent = mainService
#         second_ssdp_server = SSDPServer(second_device)  # SSDP
#         mainService.services.append(second_ssdp_server)
#         second_ssdp_server.parent = mainService
#     else:
#         raise Exception('Bad multimedia type')
#     device.datadir = args['datadir']
#     upnp_server = UPnPService(device)  # UPnP
#     mainService.services.append(upnp_server)
#     upnp_server.parent = mainService
#     ssdp_server = SSDPServer(device)  # SSDP
#     mainService.services.append(ssdp_server)
#     ssdp_server.parent = mainService
# #     if config.lirc_emitter == config.lirc_receiver:
# #         lircd = lircService(device, config.lirc_receiver, 0.2)
# #     else:
# #         if config.lirc_emitter == '' or config.lirc_emitter == 'fake':
# #             lircd = lircService(device,
# #                            config.lirc_receiver, 0.2, simul=True)
# #         else:
# #             lircd = lircService(
# #                 device, config.lirc_receiver, 0.2, direction='receiver')
# #             lirc = lircService(
# #                 device, config.lirc_emitter, 0.2, direction='emitter')
# #             pyrendererService.addService(lirc)
# #             lirc.parent = pyrendererService
# #     pyrendererService.addService(lircd)
# #     lircd.parent = pyrendererService
# #     upnp_server = UPnPService(device)  # UPnP
# #     mainService.services.append(upnp_server)
#     mainService.register_art_url = upnp_server.register_art_url
#     upnp_server.parent = mainService
#     ssdp_server = SSDPServer(device)  # SSDP
#     mainService.services.append(ssdp_server)
#     ssdp_server.parent = mainService
#     return mainService
