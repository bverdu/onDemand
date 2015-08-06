# encoding: utf-8
# !/usr/bin/python2.7
'''
Created on 5 mai 2015

@author: babe
'''

import kivy
import json
import os
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from kivy.core.window import Window
from kivy.properties import ObjectProperty,\
    StringProperty, ListProperty, DictProperty
from kivy.uix.screenmanager import ScreenManager
from widgets import StartPage, LightButton, PlayerButton, SettingPos,\
    SettingImg, Home, HVAC, Shutters, Scenarios, SensorPad  # @UnusedImport
from kivy.logger import Logger
from kivy.support import install_twisted_reactor
install_twisted_reactor()

from onDemand.controller import Controller as Oc  # @IgnorePep8
from mediaplayer import MediaPlayer  # @IgnorePep8 @UnusedImport
from onDemand.utils import FakeSensor


kivy.require('1.8.0')
install_twisted_reactor()

defaultpath = ('/sdcard/' if platform == 'android' else '~')
__version__ = '0.1'


class Controller(BoxLayout):
    '''
    Create a controller that receives a custom widget from the kv lang file.

    Add an action to be called from the kv lang file.
    '''
    menu_items = ['Home', 'HVAC', 'Shutters', 'MediaPlayer', 'Scenarios']
    sm = ScreenManager()
    ssdp = ''
    rooms = DictProperty()
    light_list = ListProperty([])
    menu = ObjectProperty()
    mediaservers = {}
    activity = StringProperty('Home')
    devices = DictProperty()
    current_device = None
    active_room = StringProperty()

    def __init__(self, app, **kwargs):
        self.app = app
        super(Controller, self).__init__(**kwargs)
        self.controller = Oc(
            self, searchables=[('upnp:rootdevice', self.on_device),
                               ('schemas-upnp-org:device:', self.on_device)],
            network='cloud',
            cloud_user=('test@xmpp.example.com', 'test'))
        self.controller.startService()
        for room, value in self.app.rooms.items():
            if room != 'New':
                self.rooms.update({room: {'devices': [], 'pic': value['pic']}})
        for item in self.menu_items:
            setattr(
                self, item.lower(),
                globals()[item](name=item,
                                controller=self.controller,
                                main_ui=self))
            self.sm.add_widget(getattr(self, item.lower()))
            getattr(self, item.lower()).realparent = self
        self.sm.current = 'Home'
        self.add_widget(self.sm)
        self.set_room('Home')

    def on_rooms(self, instance, value):
        self.ids.active_room.values = value

    def on_device(self, device):

        def on_product(product, device, typ):
            if 'Source' in typ or 'MediaRenderer' in typ:
                devtype = 'MediaPlayer'
            elif 'BinaryLight' in typ:
                devtype = 'Lights'
            else:
                Logger.debug('unknown type: %s' % typ)
                return
            try:
                room = product.Room
                name = device[device.keys()[0]]['name']
                if name in self.app.devices:
                        pos = self.app.devices[name]['pos']
                else:
                    pos = '50*50'
#                 name = product.Name
            except AttributeError:
                Logger.info(
                    'Device %s does not have room property' % device.keys()[0])
            else:
                device[device.keys()[0]].update({'room': room, 'pos': pos})
                self.devices.update(device)
                if room in self.rooms:
                    self.rooms[room]['devices'].append(
                        {'name': name,
                         'type': devtype,
                         'uid': device.keys()[0],
                         'pos': pos})
                else:
                    self.rooms.update(
                        {room: {'devices': [{'name': name,
                                             'type': devtype,
                                             'uid': device.keys()[0],
                                             'pos': pos}],
                                'pic': 'data/living.png'}})
                if room not in self.app.config.sections():
                    self.app.config.set('New', 'name', room)
                if name not in self.app.config.sections():
                    self.app.config.adddefaultsection(name)
                self.app.config.set(name, 'cat', 'device')
                self.app.config.set(name, 'name', name)
                self.app.config.set(name, 'room', room)
                self.app.config.set(name, 'position', pos)
                if self.sm.current == 'Home':
                    if room == self.active_room:
                        self.set_room(room)
                if self.active_room == 'Home':
                    if len(self.home.children) > 0:
                        self.home.children[0].roomlist = self.rooms
                        self.home.children[0].devices = self.devices

        for name, infos in device.items():
            Logger.debug(name)
            room = False
            for service in infos['services']:
                Logger.debug(service)
                if service == u'urn:av-openhome-org:service:Product:1' or \
                        service == 'urn:av-openhome-org:service:Product:1':
                    room = True
                    d = self.controller.call(device, service, 'Product')
                    d.addCallback(on_product, device, infos['devtype'])

            if not room:
                if name not in self.devices:
                    if 'Source' in infos['devtype']\
                            or 'MediaRenderer' in infos['devtype']:
                        devtype = 'MediaPlayer'
                    elif 'BinaryLight' in infos['devtype']:
                        devtype = 'Lights'
                    elif 'MediaServer' in infos['devtype']:
                        self.mediaservers.update(
                            {infos['name']: {'uid': name}})
#                         self.devices.update(device)
                        return
                    else:
                        Logger.debug('unknown type: %s' % infos['devtype'])
                        return
                    if infos['name'] in self.app.devices:
                        room = self.app.devices[infos['name']]['room']
                        pos = self.app.devices[infos['name']]['pos']
                    else:
                        room = 'unknown'
                        pos = '50*50'
                    device[device.keys()[0]].update({'room': room, 'pos': pos})
                    if room in self.rooms:
                        self.rooms[room]['devices'].append(
                            {'name': infos['name'], 'type': devtype,
                             'uid': name,
                             'pos': pos})
                    else:
                        self.rooms.update(
                            {room: {'devices': [{'name': infos['name'],
                                                 'type': devtype,
                                                 'uid': name,
                                                 'pos': pos}],
                                    'pic': 'data/living.png'}})
                    if room not in self.app.config.sections():
                        self.app.config.set('New', 'name', room)
                    self.devices.update(device)
                    if self.sm.current == 'Home':
                        if self.active_room == room:
                            self.set_room(room)
                try:
                    room = device[device.keys()[0]]['room']
                    pos = device[device.keys()[0]]['pos']
                    if infos['name'] not in self.app.config.sections():
                        self.app.config.adddefaultsection(infos['name'])
                    self.app.config.set(infos['name'], 'cat', 'device')
                    self.app.config.set(infos['name'], 'name', infos['name'])
                    self.app.config.set(infos['name'], 'room', room)
                    self.app.config.set(infos['name'], 'position', pos)
                except KeyError:
                    Logger.info('bad device: %s' % str(device))

        if self.active_room == 'Home':
            if len(self.home.children) > 0:
                self.home.children[0].roomlist = self.rooms
                self.home.children[0].devices = self.devices

    def set_room(self, room):
        print('room: %s' % room)
        if room in self.app.rooms:
            self.home.background = self.app.rooms[room]['pic']
#             print(self.app.rooms[room]['pic'])
#         print(s.ids)
        if self.active_room == room:
            print('1')
            s = self.home.children[0]
            nids = []
            for device in self.rooms[room]['devices']:
                nids.append(device['uid'])
                if device['uid'] not in s.ids:
                    if device['type'] == 'Lights':
                        b = LightButton(
                            name=device['name'],
                            size=(self.height/10, self.height/10),
                            size_hint=(None, None),
                            play=self.set_light,
                            config=self.app.config)
                    else:
                        b = PlayerButton(
                            name=device['name'],
                            size=(self.height/10, self.height/10),
                            size_hint=(None, None),
                            play=self.set_player,
                            config=self.app.config,
                            open=lambda: self.set_device(device))
                    b.id = device['uid']
                    b.device = {device['uid']: self.devices[device['uid']]}
                    b.name = device['name']
                    pos = [float(c) for c in device['pos'].split('*')]
#                     print(s.to_local(*pos))
                    b.pos = pos
#                     print(pos)
                    s.add_widget(b)
                    s.ids.update({b.id: b})
                if 'state' in self.devices[device['uid']]:
                    print('ooo')
                    s.ids[device['uid']].state = self.devices[
                                                    device['uid']]['state']
                else:
                    print('iiii')
                    if device['type'] == 'Lights':
                        d = self.controller.call(
                            {device['uid']: self.devices[device['uid']]},
                            'urn:schemas-upnp-org:service:SwitchPower:1',
                            'GetTarget')
                        d.addCallback(self.update_light, device['uid'])
                    else:
                        d = self.controller.call(
                            {device['uid']: self.devices[device['uid']]},
                            'urn:av-openhome-org:service:Playlist:1',
                            'TransportState')
                        d.addCallback(self.update_player, device['uid'])
                if device['type'] == 'Lights':
                    self.controller.subscribe(
                        {device['uid']: self.devices[device['uid']]},
                        'urn:schemas-upnp-org:service:SwitchPower:1',
                        'Status',
                        self.update_light,
                        device['uid'])
                else:
                        self.controller.subscribe(
                            {device['uid']: self.devices[device['uid']]},
                            'urn:av-openhome-org:service:Playlist:1',
                            'TransportState',
                            self.update_player,
                            device['uid'])
                if len(s.ids) > len(self.rooms[room]['devices']):
                    for w in s.children:
                        if w.id not in nids:
                            s.remove_widget(w)
                            del(s.ids[w.id])
        else:
            print('2')
#             s.clear_widgets()
            self.home.clear_widgets()
#             s = None
            self.active_room = room
            if room == 'Home':
                s = StartPage(
                    roomlist=self.rooms, do_scroll_x=False)
                self.sm.current = 'Home'
                self.home.add_widget(s)
                return
            else:
                s = FloatLayout(id='icons')
            s.ids = {}
            self.home.add_widget(s)
            for device in self.rooms[room]['devices']:
                if device['type'] == 'Lights':
                    #  b = NewLightButton(play=self.set_light)
                    b = LightButton(
                        name=device['name'],
                        size=(self.height/10, self.height/10),
                        size_hint=(None, None),
                        play=self.set_light,
                        config=self.app.config)
                    #  b.ids.light_name.text = device['name']
                else:
                    b = PlayerButton(
                            name=device['name'],
                            size=(self.height/10, self.height/10),
                            size_hint=(None, None),
                            play=self.set_player,
                            config=self.app.config,
                            open=lambda: self.set_device(device))
                b.id = device['uid']
                b.device = {device['uid']: self.devices[device['uid']]}
                if device['type'] == 'Lights':
                    self.controller.subscribe(
                        b.device, 'urn:schemas-upnp-org:service:SwitchPower:1',
                        'Status', self.update_light, b.id)
                else:
                    self.controller.subscribe(
                            b.device,
                            'urn:av-openhome-org:service:Playlist:1',
                            'TransportState',
                            self.update_player,
                            b.id)
#                     b.bind(on_press=lambda x: self.set_device(device))
                if 'state' in self.devices[b.id]:
                    b.state = self.devices[b.id]['state']
                else:
                    print('iiii')
                    if device['type'] == 'Lights':
                        d = self.controller.call(
                            {device['uid']: self.devices[device['uid']]},
                            'urn:schemas-upnp-org:service:SwitchPower:1',
                            'GetTarget')
                        d.addCallback(self.update_light, device['uid'])
                    else:
                        d = self.controller.call(
                            {device['uid']: self.devices[device['uid']]},
                            'urn:av-openhome-org:service:Playlist:1',
                            'TransportState')
                        d.addCallback(self.update_player, device['uid'])
                pos = [float(c) for c in device['pos'].split('*')]
#                 print(pos)
                b.pos = pos
                b.name = device['name']
#                 print(pos)
                s.add_widget(b)
#                 print(s.ids)
                s.ids.update({b.id: b})
            sensors = SensorPad(size=((self.width/7, self.height/5)
                                      if self.width > self.height
                                      else (self.width/3, self.height/3)),
                                size_hint=(None, None),
                                pos=([self.width * .85, self.height * .7]
                                     if self.width > self.height
                                     else [self.width * .6, self.height * .7]))
            sensors.sensors = [FakeSensor('temp', '°C', '32'),
                               FakeSensor('Presence', None, True),
                               FakeSensor('Luminosity', '%', '60'),
                               FakeSensor('Humidity', '%', '40')]
            s.add_widget(sensors)
            self.sm.current = 'Home'

    def update_light(self, new_stat, objid):
        Logger.debug('Light :%s ----> %s' % (str(objid), str(new_stat)))
#         state = ('down' if new_stat else 'normal')
        state = bool(int(new_stat))
        if 'state' in self.devices[objid]:
            self.devices[objid]['state'] = state
        else:
            self.devices[objid].update({'state': state})
        childs = self.home.children
        if len(childs) > 0:
            for child in childs[0].children:
                if child.id == objid:
                        #  child.state = new_stat
                    child.state = state

    def all_lights_off(self):
        print("all off")

    def set_light(self, btn):
        new = btn.state
#         new = (btn.state == 'down')
        self.controller.call(
            btn.device, 'urn:schemas-upnp-org:service:SwitchPower:1',
            'SetTarget', new)

    def update_player(self, new_stat, objid):
        Logger.debug('Player :%s ----> %s' % (str(objid), str(new_stat)))
        state = (True if new_stat == 'Playing' else False)
#         state = new_stat
        if 'state' in self.devices[objid]:
            self.devices[objid]['state'] = state
        else:
            self.devices[objid].update({'state': state})
        childs = self.home.children
        if len(childs) > 0:
            for child in childs[0].children:
                if child.id == objid:
                        #  child.state = new_stat
                    child.state = state

    def set_player(self, btn):
        new = btn.state
#         new = (btn.state == 'down')
        if new:
            self.controller.call(
                btn.device, 'urn:av-openhome-org:service:Playlist:1',
                'Play')
        else:
            self.controller.call(
                btn.device, 'urn:av-openhome-org:service:Playlist:1',
                'Pause')

    def set_device(self, device):
        try:
            self.sm.current = device['type']
            self.controller.current_device = device
        except:
            return

    def remove_device(self, uid):
        for room, values in self.rooms.items():
            for device in values['devices']:
                if device['uid'] == uid:
                    self.rooms[room]['devices'].remove(device)
                    if len(self.rooms[room]['devices']) > 0:
                        if self.controller.current_device and\
                                uid == self.controller.current_device['uid']:
                            self.set_room(room)
                    else:
                        del self.rooms[room]
                        self.set_room(self.rooms.keys()[0])
                        self.ids.active_room.text = self.rooms.keys()[0]
#                     print(self.devices)
                    del self.devices[uid]
                    self.controller.devices.remove(uid)

    def test(self, x):
        print(x.text)


class KontrollerApp(App):
    sections = {}
    rooms = {}
    devices = {}
    use_kivy_settings = False
    root = None

    def build(self):
        config = self.config
#         config.add_callback(self.update_conf)
        for section in config.sections():
            for option in config.options(section):
                self.config.set(section, option, config.get(section, option))
#              self.update_conf(section, option, config.get(section, option))
        self.icon = 'data/icons/logo3.png'
        self.title = 'onDemand Controller'
        Window.bind(on_close=self.clean_state)
        self.root = Controller(self)
        return self.root

    def build_config(self, config):
        config.add_callback(self.update_conf)
        config.setdefaults('Rooms', {
            'cat': 'map',
            'names': 'New,Home'
        })
        config.setdefaults('New', {
            'cat': 'room',
            'name': 'New',
            'pic': os.path.join(self.directory, 'data/living.png')
        })
        config.setdefaults('Home', {
            'cat': 'room',
            'name': 'Home',
            'pic': os.path.join(
                self.directory, 'data/background_ebony.png')
        })
        config.setdefaults('local', {
            'cat': 'local',
            'name': 'Media Path',
            'stype': 'path',
            'mediapath': defaultpath
        })

    def build_settings(self, settings):
        settings.register_type('pos', SettingPos)
        settings.register_type('path', SettingImg)
        devices = []
        rooms = []
        localsettings = []
#         print('build settings: %s' % self.sections)
        for s, v in self.sections.items():
            if 'cat' in v:
                if v['cat'] == 'device':
                    devices.append({'type': 'title', 'title': v['name']})
                    self.devices.update(
                        {v['name']: {'room': v['room'], 'pos': v['position']}})
                    devices.append({
                        'type': 'options',
                        'title': 'Room',
                        'desc': 'Set the room in where %s is located'
                        % v['name'],
                        'section': s,
                        'key': 'room',
                        'options': self.rooms.keys()})
                    devices.append({
                        'type': 'pos',
                        'title': 'Position',
                        'desc': 'Set the Position of the device',
                        'pic': self.rooms[v['room']]['pic'],
                        'section': s,
                        'key': 'position'})
                elif v['cat'] == 'room':
                    if 'pic' not in v:
                        return
                    rooms.append({'type': 'title', 'title': v['name']})
                    rooms.append({
                        'type': 'string',
                        'title': 'Name',
                        'desc': 'Name of the room',
                        'section': v['name'],
                        'key': 'name'})
                    rooms.append({
                        'type': 'path',
                        'title': 'Background',
                        'desc': 'Picture of the room',
                        'section': v['name'],
                        'key': 'pic'})
                elif v['cat'] == 'local':
                    localsettings.append({
                        'type': v['stype'],
                        'title': v['name'],
                        'section': s,
                        'key': 'mediapath'})
        if len(devices) > 0:
            confdev = json.dumps(devices)
            settings.add_json_panel('Devices',
                                    self.config, data=confdev)
        if len(rooms) > 0:
            #             print(rooms)
            confrooms = json.dumps(rooms)
            settings.add_json_panel('Rooms',
                                    self.config, data=confrooms)
        if len(localsettings) > 0:
            #             print(localsettings)
            conflocals = json.dumps(localsettings)
            settings.add_json_panel('Local Settings',
                                    self.config, data=conflocals)

    def update_conf(self, section, key, value):
        try:
            section = section.encode('utf-8')
        except:
            section = section
        try:
            value = value.encode('utf-8')
        except:
            value = value
        open_ = False
        if section == 'Rooms':
            if key == 'names':
                for v in value.split(','):
                    if v not in self.rooms:
                        self.rooms.update({v: {}})
                        self.config.adddefaultsection(v)
#                         self.config.set(v, 'name', v)
            return
        if section in self.sections:
            if section == 'New':
                if key == 'name':
                    if value == 'New':
                        self.sections[section].update({key: value})
                        return
                    if value not in self.rooms:
                        self.sections.update({value: {}})
                        self.rooms.update(
                            {value: {'name': value,
                                     'pic': os.path.join(
                                         self.directory, 'data/living.png')}})
                        self.config.adddefaultsection(value)
                        self.config.set(value, 'name', value)
                        self.config.set(value, 'cat', 'room')
                        self.config.set(
                            value,
                            'pic',
                            os.path.join(self.directory, 'data/living.png'))
                        self.config.set(
                            'Rooms', 'names', ','.join(self.rooms.keys()))
                    section = value
                    self.config.set('New', 'name', 'New')
            self.sections[section].update({key: value})
        else:
            self.sections.update({section: {key: value}})
            self.config.adddefaultsection(section)
#             self.config.set(section, key, value)
            return
        if 'cat' in self.sections[section]:
            if self.sections[section]['cat'] == 'room':
                if 'name' in self.sections[section]:
                    if section != self.sections[section]['name']:
                        newsec = self.sections[section]['name']
                        del(self.sections[section])
                        del self.rooms[section]
                        self.rooms.update({newsec: {}})
                        if self.root:
                            self.root.rooms.update({newsec: {}})
                        self.config.remove_section(section)
                        self.config.adddefaultsection(newsec)
                        self.config.set(newsec, 'name', newsec)
                    self.config.set(
                        'Rooms', 'names', ','.join(self.rooms.keys()))
        if 'room' in self.sections[section]:
            room = self.sections[section]['room']
            if section in self.devices:
                self.devices[section].update({'room': room})
            else:
                self.devices.update({section: {'name': section, 'room': room}})
            if self.root:
                device = None
                for r, v in self.root.rooms.items():
                    if r == room:
                        continue
                    for d in v['devices']:
                        if d['name'] == self.sections[section]['name']:
                            device = d
                            v['devices'].remove(d)
                            self.root.rooms[room].update(
                                {'devices': v['devices']})
                            break
                if device:
                    if room in self.root.rooms:
                        self.root.rooms[room]['devices'].append(device)
                    else:
                        if room in self.rooms:
                            self.root.rooms.update(
                                {room: {'devices': [device],
                                        'pic': self.rooms[room]['pic']}})
                        else:
                            self.root.rooms.update(
                                {room: {'devices': [device],
                                        'pic': 'data/living.png'}})
        if 'position' in self.sections[section]:
            if section in self.devices:
                self.devices[section].update(
                    {'pos': self.sections[section]['position']})
            else:
                self.devices.update(
                    {section:
                     {'name': section,
                      'pos': self.sections[section]['position']}})
            if self.root:
                if 'room' in self.sections[section]:
                    if self.sections[section]['room'] == self.root.home.room:
                        for device in self.root.home.ids.icons.children:
                            if device.name == section:
                                pos = [float(c) for c in
                                       self.sections[section]['position']
                                       .split('*')]
                                device.pos = pos
        if 'pic' in self.sections[section]:
            room = section
            if room in self.rooms:
                self.rooms[room].update({'pic': self.sections[section]['pic']})
            else:
                self.rooms.update(
                    {room: {'pic': self.sections[section]['pic']}})
            if self.root:
                if room == self.root.home.room:
                    self.root.home.background = self.sections[section]['pic']
        try:
            cat = self.sections[section]['cat']
            if cat == 'device':
                if len(self.sections[section].keys()) < 3:
                    return
            elif cat == 'room':
                if len(self.sections[section].keys()) < 2:
                    return
        except KeyError:
            return
        if self.close_settings():
            open_ = True
        self.destroy_settings()
        if open_:
            self.open_settings()

    def on_pause(self, *args, **kwargs):
        #         self.root.controller.clean()
        Logger.debug('on pause')
        self.root.controller.stopService()
        return True

    def on_resume(self, *args, **kwargs):
        self.root.controller.startService()

    def clean_state(self, *args, **kwargs):
        self.root.controller.clean()


if __name__ == '__main__':
    root = KontrollerApp()
    window = root.run()
