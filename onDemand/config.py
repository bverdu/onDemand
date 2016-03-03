'''
Created on 12 nov. 2014

@author: Bertrand Verdu
'''

# User variables

rooms = {}
hmodules = {}
cloudmodules = {}
triggers = {}
protocol = 'oh'
media_types = []
auto = {}
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
cloud_user = 'test@xmpp.example.com'
cloud_secret = 'password'
datadir = '/usr/share/onDemand/'
custom_services = {}


# imports = '''
# from onDemand.%s import %s
# player = %s
# '''
# exec imports % (playertype.split()[0],
#                 playertype.split()[0].capitalize(),
#                 playertype.split()[0].capitalize())
