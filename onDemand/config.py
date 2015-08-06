'''
Created on 12 nov. 2014

@author: babe
'''

# User variables

rooms = {}
hmodules = {}
triggers = {}
protocol = 'oh'
media_types = []
# multimediatype = 'UPnP'
lirc_receiver = '/var/run/lirc/lircd'
lirc_emitter = 'fake'
state = []
cancellable = {}
last = 'stop'
#client = 'mpdclient'
client = 'mpdclient'
player = None
client_opts = 'addr=192.168.0.9, port=6600'
clients = ['mprisclient', 'omxclient', 'mpdclient', 'control', 'mediaserver']
shared_dirs = ['/home/babe/Projets/eclipse/onDemand/']
network = 'lan'
cloud_user = 'test@xmpp.bertrandverdu.me'

# imports = '''
# from onDemand.%s import %s
# player = %s
# '''
# exec imports % (playertype.split()[0],
#                 playertype.split()[0].capitalize(),
#                 playertype.split()[0].capitalize())
