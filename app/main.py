# encoding: utf-8
'''
Created on 22 août 2015

@author: Bertrand Verdu
'''
import os
import json
import kivy
import socket
from kivy.app import App, platform
from kivy.properties import ListProperty, StringProperty, ObjectProperty, \
    BooleanProperty, DictProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.carousel import Carousel
from kivy.support import install_twisted_reactor
from twisted.protocols.amp import UNKNOWN_ERROR_CODE
install_twisted_reactor()
from device.weather import WeatherBox  # @UnusedImport @IgnorePep8
from onDemand.plugins.weather import Weather as Weather_api  # @IgnorePep8
from onDemand.util.data import remove_unicode  # @IgnorePep8
from twisted.protocols.amp import AMP  # @IgnorePep8
from twisted.internet import reactor  # @IgnorePep8
from twisted.internet.protocol import Factory  # @IgnorePep8
from twisted.internet.endpoints import TCP4ClientEndpoint  # @IgnorePep8
# @IgnorePep8
from upnpy_spyne.controller import StartController, GetDevices, Event, DeviceInfo

kivy.require('1.9.0')
__version__ = '0.1'


def _(text):
    '''
    For compatibility with gettext
    '''
    return(text)


class App_carousel(Carousel):
    direction = 'right'
    loop = True


class Main(BoxLayout):

    landscape = BooleanProperty(True)
    background = StringProperty('data/graphics/background.png')
    default = StringProperty()
    previous = StringProperty()
    current = ObjectProperty()
    menu_items = ListProperty()
#     sm = ScreenManager()
    cr = App_carousel()
    connection_type = StringProperty('local')
    failconnect = 0
    devices = {}
    _locations = {}
    location = StringProperty('')
    locations = ListProperty()
    old_locations = []
    weather = ObjectProperty()
    slide_index = DictProperty({})

    def __init__(self, app, **kwargs):
        super(Main, self).__init__()
        self.config = app.config
        self.config.add_callback(self.on_config)
        for loc in [e.strip().strip('\'')
                    for e in self.config.get(
                'Locations',
                'locations')[1:-1].split(',')]:
            items = loc.split('(')
            print(items)
            name = self.config.get(loc, 'name')
            l = self.config.get(loc, 'location')
#             name = items[0]
#             l = items[1].strip(')')
            self._locations.update({name: l})
            self.locations.append(name)
        self.previous = ''
        self.default = self.config.get(self.config.get(
            'Locations',
            'default'), 'name')
        if self._locations[self.default]:
            self.location = self._locations[self.default]
        self.menu_items = self.locations
        self.landscape = (self.width >= self.height)
        self.change_orientation()
        self.cr.slide_index = {}
        self.add_widget(self.cr)
        self.connect()
        
    def on_config(self, section, key, value):
        print('%s: %s --> %s' % (section, key, value))

    def on_location(self, inst, value):
        print('***********New Location***********%s' % value)
        
    def on_locations(self, inst, value):
        self.menu_items = value
        print(value)
        print(self.old_locations)
        if len(value) > len(self.old_locations):
            i = len(self.cr.slides)
            new = [l for l in value if l not in self.old_locations]
            for loc in new:
                self.cr.add_widget(
                Location(
                    name=loc,
                    landscape=self.landscape,
                    location=self._locations[loc]))
                self.slide_index.update({loc: i})
                i += 1
        else:
            new = [l for l in self.old_locations if l not in value]
            for loc in new:
                for w in self.cr.slides:
                    if loc == w.name:
                        self.cr.remove_widget(w)
                del self.slide_index[loc]
        if self.default in value:
            self.cr.index = self.slide_index[self.default]
        else:
            print('not a location')
        print(self.slide_index)
        print(self.cr.slides)
        self.old_locations = [l for l in value]
        

    def on_device(self, d, uid):
#         if isinstance(res, dict):
#             res = res['value']
#         if not isinstance(res, list):
#             res = [res]
        print('new device : %s: %s' % (uid, d))
        if not isinstance(d, dict):
            try:
                d = json.loads(d, encoding='utf-8')
            except:
                print ('bad device: %s' % d)
                return
        ignored = True
        if 'devtype' in d:
            if d['devtype'] in ('Source', 'BinaryLight', 'HVAC_System',
                        'HVAC_ZoneThermostat', 'MediaRenderer',
                        'SensorManagement'):
                ignored = False
        d.update({'ignored': ignored})
        self.devices.update({'uid': d})
        if 'loc' in d and d['loc']:
            country, city, name, room = d['loc'].split('/')
        else:
            name = 'Unknown'
            room = 'Unknown'
            country = 'France'
            city = 'Marseille'
        if name not in self._locations:
            self._locations.update({name: '/'.join((country, city))})
            self.locations.append(name)
        elif self._locations[name] != '/'.join((country, city)):
            if self._locations[name][-1].isdigit():
                name = self._locations[name] + '_' + bytes(
                                            int(self._locations[name][-1] + 1))
            else:
                name = self._locations[name] + '_1'
            self._locations.update({name: '/'.join((country, city))})
            self.locations.append(name)
        print('device %s in room %s at %s found' % (d['name'], room, name))
        for loc in self.cr.slides:
#             print(loc.name)
#             print(name)
            if loc.name == name:
#                 print('bingooooo')
#                 print(loc.devices)
                loc.devices.append(d)
            
                
#         if uid in self.devices:
#             self.devices.update({uid: res})
#         else:
#         self.devices.update({uid: res})
#         for data in res:
#             val = data.split(':')
#             v = ':'.join(val[1:])
#             print('new device : %s, %s=%s' % (uid, val[0], v))
#             if uid in self.devices:
#                 self.devices[uid].update({val[0]: v})
#             else:
#                 self.devices.update({uid: {val[0]: v}})
#             if val[0] == 'devtype':
#                 v = ':'.join(val[1:])
#                 for item in ('Source', 'BinaryLight',
#                              'HVAC_System', 'HVAC_ZoneThermostat',
#                              'MediaRenderer', 'SensorManagement'):
#                     if item in v:
#                         self.devices[uid].update({'ignored': False})
#                     else:
#                         self.devices[uid].update({'ignored': True})
#             if val[0] == 'loc':
#                 country, city, name, room = v.split('/')
#                 if name not in self._locations:
#                     self._locations.update({name: '/'.join((country, city))})
#                     self.locations.append(name)

    def connect(self):
        print('1')
        endpoint = TCP4ClientEndpoint(
            reactor, "127.0.0.1", 4343)
        self.amp = ClientFactory(self)
        self.amp.register_event('device', self.on_device)
        d = endpoint.connect(self.amp)
        print(d)
        d.addCallbacks(self.connected, self.not_connected)

    def not_connected(self, err, ignored=None):
        print(self.failconnect)
        if self.failconnect > 9:
            raise Exception('Unable to connect to service')
        self.failconnect += 1
        reactor.callLater(1, self.connect)  # @UndefinedVariable

    def connected(self, protocol, ignored=None):
        self.failconnect = 0
        self.controller_service = protocol
        jid = '@'.join((bytes(self.config.getdefault(
            'Connection Settings', 'cloud_user', 'user')),
            bytes(self.config.getdefault(
                'Connection Settings', 'cloud_server',
                'xmmp.example.org'))))
        s = protocol.callRemote(StartController,
                                search_type='upnp:rootdevice',
                                search_name='',
                                network=bytes(self.config.getdefault(
                                    'Connection Settings',
                                    'type',
                                    'lan')),
                                cloud_user=jid,
                                cloud_pass=bytes(self.config.getdefault(
                                    'Connection Settings',
                                    'cloud_pwd',
                                    'password')))
        s.addCallback(self.started)

    def show(self, res):
        print(res)
        return res

    def check_devices(self, devices):
        for device in devices['devices']:
            d = json.loads(device, encoding='utf-8')
            for k, v in d.iteritems():
                if k not in self.devices:
                    self.on_device(v, k)
#             if device not in self.devices:
#                 print('check 1')
#                 d = self.controller_service.callRemote(DeviceInfo, uuid=device)
#                 d.addCallback(self.on_device, device)

    def started(self, started):
        #         print(started['started'])
        if started:
            d = self.controller_service.callRemote(GetDevices,
                                                   dev_type='')
            d.addCallback(self.show)
            d.addCallback(self.check_devices)

    def change_orientation(self):

        if len(self.cr.slides) > 0:
            for w in self.cr.slides:
                w.change_orientation(self.landscape)
            return
#         else:
#             i = 0
#             current = self.default
#             print(self.locations)
#             for loc in self.locations:
#                 self.cr.add_widget(
#                     Location(
#                         name=loc,
#                         landscape=self.landscape,
#                         location=self._locations[loc]))
#                 self.slide_index.update({loc: i})
#                 i += 1
#         if current in self.locations:
#             self.cr.index = self.slide_index[current]
#         else:
#             print('not a location')
#         print(self.slide_index)
#         print(self.cr.slides)

    def on_size(self, *args, **kwargs):

        if not (self.width >= self.height) is self.landscape:
            self.landscape = (self.width >= self.height)
            self.change_orientation()

    def prev(self):

        if self.cr.current_slide.typ == 'location':
            current = self.default
        else:
            current = self.sm.current_slide.parent.name
        self.set_current(current)

    def set_current(self, value):

        if value == self.default:
            self.previous = ''
        else:
            if self.cr.current_slide.typ == 'location':
                self.previous = self.default
            else:
                self.previous = self.cr.current_slide.parent.name
        if value in self.slide_index:
            self.location = self._locations[value]
            self.cr.index = self.slide_index[value]

    def toggle_connection(self):

        if self.connection_type == 'local':
            self.connection_type = 'cloud'
        else:
            self.connection_type = 'local'


class ClientAmp(AMP):

    @Event.responder
    def on_event(self, name, id_, value):
        self.parent.receive(name, id_, value)
        return {}


class ClientFactory(Factory):

    protocol = ClientAmp

    def __init__(self, parent):
        self.events_callers = {}
        self.protocol.parent = self
#         Factory.__init__(self)

    def register_event(self, name, callbck):
        self.events_callers.update({name: callbck})

    def receive(self, name, id_, value):
        if name in self.events_callers:
            self.events_callers[name](value, id_)

    def call(self, *args, **kwargs):
        self.protocol.callRemote(*args, **kwargs)


class Location(RelativeLayout):

    typ = 'location'
    landscape = BooleanProperty(True)
    background = StringProperty()
    location = StringProperty()
    name = StringProperty()
    devices = ListProperty()

    def __init__(self, *args, **kwargs):
        super(Location, self).__init__(**kwargs)
        try:
            background = '/'.join((os.path.dirname(__file__), 'data/graphics/' + self.name.decode(
                'utf-8')))
        except UnicodeEncodeError:
            background = '/'.join((os.path.dirname(__file__), 'data/graphics/' + self.name.encode(
                'utf-8')))
        print(background)
        if os.path.exists(background + '.png'):
            self.background = background + '.png'
        elif os.path.exists(background + '.jpg'):
            self.background = background + '.jpg'
        else:
            self.background = 'data/graphics/Unknown.png'
        print(self.background)
        self.change_orientation(self.landscape)
#         if self.landscape:
#             
#             self.add_widget(
#                 Loc_landscape(name=self.name, location=self.location))
#         else:
#             ext = self.background[-4:]
#             self.background = self.background[:-6] + '_p' + ext
#             self.add_widget(
#                 Loc_portrait(name=self.name,  location=self.location))
            
    def on_devices(self, inst, value):
        print('....................%s...................' % value)

    def change_orientation(self, landscape=True):
        self.clear_widgets()
        if landscape:
            if self.background[-6:-4] == '_p':
                self.background = self.background[:-6] + self.background[-4:]
            self.add_widget(
                Loc_landscape(name=self.name,  location=self.location))
        else:
            ext = self.background[-4:]
            self.background = self.background[:-4] + '_p' + ext
            print(self.background)
            self.add_widget(
                Loc_portrait(name=self.name,  location=self.location))


class Loc_portrait(BoxLayout):
    name = StringProperty()
    location = StringProperty()


class Loc_landscape(BoxLayout):
    name = StringProperty()
    location = StringProperty()


class mainApp(App):
    use_kivy_settings = False
    sections = []
    defaults = {
        'locations': 'Home', 'rooms': 'Living-Room', 'devices': 'device-name'}

    def build(self):
        config = self.config
        self.icon = 'data/graphics/icons/logo.png'
        self.title = 'onDemand Controller'
        self.weather = Weather_api(key=config.getdefault('hidden',
                                                         'weatherapikey',
                                                         '12345678'))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        t = s.connect_ex(('127.0.0.1', 4343))
        if t != 0:
            print(platform)
            if platform == 'android':
                from android import AndroidService  # @UnresolvedImport
                service = AndroidService('Controller service', 'running')
                service.start('service started')
                self.service = service
            else:
                import subprocess
                print(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'service/main.py'))
                stat = subprocess.Popen(
                    ['/usr/bin/python2',
                     os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'service/main.py')],
                    close_fds=True)
                print(stat)
        return Main(self)

    def build_config(self, config):

        config.add_callback(self.update_conf)

        config.setdefaults('hidden', {
            'counter': 0,
            'weatherApiKey': '12345678'})

        config.setdefaults('Locations', {
            'default': 'b744e767-72dd-45a5-91af-0d4fc6bd318b',
            'locations': ['b744e767-72dd-45a5-91af-0d4fc6bd318b'],
            'parent': None})

        config.setdefaults('Connection Settings', {
            'type': 'lan',
            'cloud_user': 'user',
            'cloud_server': 'xmpp.example.org',
            'cloud_pwd': 'password'})

    def build_settings(self, settings):
        print(self.sections)
        for section in self.sections:
            if section == 'hidden':
                continue
            title = section
            s = []
            for name, value in self.config.items(section):
                if name == 'real_name':
                    title = value
                    continue
                if name in ('id', 'parent'):
                    continue
                typ = 'string'
                if value == 'False' or value == 'True':
                    typ = 'bool'
                s.append(
                    {'type': typ,
                     'title': name,
                     'key': name,
                     'section': section})
#             if 'long_name' in d:
#                 title = d['long_name']
            data = json.dumps(s)
#             print(data)
            settings.add_json_panel(title,
                                    self.config, data=data)

    def update_conf(self, section, key, value):
        open_ = False
#         print('%s -- %s -- %s' % (self.sections, section, key))
        if section not in self.sections:
            self.sections.append(section)
        if key == 'locations':
            itemtype = 'rooms'
            prefix = 'l'
        elif key == 'rooms':
            itemtype = 'devices'
            prefix = 'r'
#         elif key == 'name':
#             if value != section.split('(')[0]:
#                 l = section.split('(')
#                 print('??%s   §§%s' % (value, l[0]))
#                 items = self.config.items(section)
#                 self.config.add_section('('.join((value,l[1])))
#                 self.config.remove_section(section)
#                 print(self.sections)
#                 self.sections.remove(section)
#                 print(self.sections)
#                 for item in items:
#                     self.config.set('('.join((value,l[1])), item[0], item[1])
#                 
#                 section = '('.join((value,l[1]))
# #                 self.sections.append(section)
#             prefix = 'd'
        else:
            prefix = 'd'
        if isinstance(value, list):
            for item in value:
                if self.config.getdefault(item, 'name', True):
                    c = int(self.config.getdefault(
                        'hidden', 'counter', '0')) + 1
                    self.config.setdefaults(item,
                                            {'parent': section,
                                             'name': 'Home',
                                             'real_name': 'Home(France/Marseille)',
                                             'location': 'France/Marseille',
                                             itemtype: [],
                                             'default': False,
                                             'id': prefix + str(c)})
                    self.config.set('hidden', 'counter', c)
                    

#         if self.close_settings():
#             open_ = True
        self.destroy_settings()
#         if open_:
#             self.open_settings()

if __name__ == '__main__':
    root = mainApp()
    window = root.run()
