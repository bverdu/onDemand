'''
Created on 6 jan. 2015

@author: Bertrand Verdu
'''
import socket
from twisted.python import usage
# from guppy import hpy
from onDemand import main, config

# h = hpy()


class Options(usage.Options):
    protocol = config.protocol
    client = config.client
    client_opts = 'addr=127.0.0.1, port=6600, program=/usr/bin/vlc'
    name = "onDemand_device - %s" % socket.gethostname()
    datadir = "/usr/share/onDemand/"

    optParameters = [['protocol',
                      'p',
                      protocol,
                      'Network protocol to use: oh (OpenHome) or upnp (UPnP)'],
                     ['name', 'n', name, 'desired device name'],
                     ['client',
                      'c',
                      client,
                      'type of slave client, should be one of: %s'
                      % ' '.join(config.clients)],
                     ['datadir', 'd', datadir,
                      "Data directory (containing icon.png)"]]
    optFlags = [['dev', 'x', 'developper mode']]


def makeService(config):
    return main.makeService(config)
