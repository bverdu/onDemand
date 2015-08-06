'''
Created on 22 janv. 2015

@author: babe
'''
import importlib
from twisted.application import service
from upnpy.upnp import UPnPService
from upnpy.ssdp import SSDPServer
from utils import load_config

import config


def makeService(args):
    '''
    Create and launch main service
    '''
#     imports = '''
# from onDemand.%s import %s
# player = %s('%s', %d)
# '''
    mainService = service.MultiService()
    player = None
    load_config(args['datadir'])
    # Take an aspirin...
    if config.client is not None:
        player = getattr(
            importlib.import_module('onDemand.'+config.client.split()[0]),
            config.client.split()[0].capitalize())(
                **{opt.split('=')[0].strip(): opt.split('=')[1].strip()
                    for opt in config.client_opts.split(',')})
        mainService.services.append(player)
        player.parent = mainService
    if config.protocol == 'upnp':
        from onDemand.UPnPdevice import MainDevice
        device = MainDevice(args["name"], player, args['datadir'])
    elif config.protocol == 'oh':
        from onDemand.ohdevice import Source
        device = Source(args["name"], player, args['datadir'])
    elif config.protocol == 'all':
        from onDemand.UPnPdevice import MainDevice  # @Reimport
        device = MainDevice(args["name"], player, args['datadir'])
        from onDemand.ohdevice import Source  # @Reimport
        second_device = Source(args["name"], player, args['datadir'])
        second_device.datadir = args['datadir']
        second_upnp_server = UPnPService(second_device)  # UPnP
        mainService.services.append(second_upnp_server)
        second_upnp_server.parent = mainService
        second_ssdp_server = SSDPServer(second_device)  # SSDP
        mainService.services.append(second_ssdp_server)
        second_ssdp_server.parent = mainService
    else:
        raise Exception('Bad multimedia type')
    device.datadir = args['datadir']
    upnp_server = UPnPService(device)  # UPnP
    mainService.services.append(upnp_server)
    upnp_server.parent = mainService
    ssdp_server = SSDPServer(device)  # SSDP
    mainService.services.append(ssdp_server)
    ssdp_server.parent = mainService
#     if config.lirc_emitter == config.lirc_receiver:
#         lircd = lircService(device, config.lirc_receiver, 0.2)
#     else:
#         if config.lirc_emitter == '' or config.lirc_emitter == 'fake':
#             lircd = lircService(device,
#                            config.lirc_receiver, 0.2, simul=True)
#         else:
#             lircd = lircService(
#                 device, config.lirc_receiver, 0.2, direction='receiver')
#             lirc = lircService(
#                 device, config.lirc_emitter, 0.2, direction='emitter')
#             pyrendererService.addService(lirc)
#             lirc.parent = pyrendererService
#     pyrendererService.addService(lircd)
#     lircd.parent = pyrendererService
    upnp_server = UPnPService(device)  # UPnP
    mainService.services.append(upnp_server)
    mainService.register_art_url = upnp_server.register_art_url
    upnp_server.parent = mainService
    ssdp_server = SSDPServer(device)  # SSDP
    mainService.services.append(ssdp_server)
    ssdp_server.parent = mainService
    return mainService
