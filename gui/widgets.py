# encoding: utf-8
'''
Created on 29 mai 2015

@author: babe
'''

from __future__ import print_function
import os
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics.transformation import Matrix
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scatter import Scatter
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.bubble import Bubble
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.settings import SettingString, SettingSpacer, SettingPath
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.image import Image
from kivy.properties import ObjectProperty,\
    StringProperty, DictProperty, BooleanProperty, ListProperty


def button_size():
    if Window.size[0] > Window.size[1]:
        return Window.size[0]/5, Window.size[1]/8
    else:
        return Window.size[0]/3, Window.size[1]/8


class Home(Screen):
    background = StringProperty('data/background_ebony.png')
    status = DictProperty()
    room = ''


class StartPage(GridLayout):
    devices = DictProperty()
    roomlist = DictProperty()
    format = ListProperty([i for i in button_size()])
    _rooms = []
    _devices = []
    rooms = None
    lights = None
    medias = None
    first = True

    def on_devices(self, instance, value):
        # print('device: %s' % value)
        for uid, device in value.items():
            if uid not in self._devices:
                for dev in self.roomlist[device['room']]['devices']:
                    if dev['uid'] == uid:
                        self.add_device(dev)

    def on_roomlist(self, instance, value):
#         print('room: %s' % value)
#         print(len(self.children))
        if len(self.children) == 0:
            def later(ignored):
                self.on_roomlist(instance, value)
#             f = lambda ignored: self.on_roomlist(instance, value)
            Clock.schedule_once(later, 2)
            return
        # print(len(self.children))
        # print(self.rooms)
        # print(self.ids)
        if not self.rooms:
            self._rooms = []
            self._devices = []
            if len(self.children) > 0:
                for child in self.children:
                    if len(child.children) > 0:
                        child = child.children[0]
                    if child.typ:
                        print(child.typ)
                        setattr(self, child.typ, child)
        for room, values in value.items():
            if room == 'Home':
                continue
            if room not in self._rooms:
                if self.rooms:
                    #  print('add room: %s -- %s' % (room, values['pic']))
                    self.add_room(room, values['pic'])
            if self.rooms:
                for device in values['devices']:
                    if device['uid'] not in self._devices:
                        # print('add device: %s' % device)
                        self.add_device(device)

    def add_room(self, room, pic):
#         print('dimensions: %s X %s' % (self.parent.width, self.parent.height))
        print('from Window: %s X %s' % Window.size)
        w = button_size()[0]
        r = RoomButton(ltext=room,
                       pic=pic,
                       width=w,
                       size_hint=(None, 1))
#                        size_hint=((.20, 1)
#                                     if Window.size[0] >= Window.size[1]
#                                     else (.4, 1)))
        self.rooms.add_widget(r)
        self._rooms.append(room)

    def add_device(self, device):
        w = button_size()[0]
        print('dimensions d : %s X %s' % (self.parent.width, self.parent.height))
        if device['type'] == 'Lights':
            if self.lights:
                b = LightButtonWithText(
                        pic=type_img(device['type']),
                        ltext=device['name'],
                        width=w,
                        size_hint=(None, 1))
#                         size_hint=((.20, 1)
#                                    if Window.size[0] >= Window.size[1]
#                                    else (.4, 1)))
                self.lights.add_widget(b)
        elif device['type'] == 'MediaPlayer':
            if self.medias:
                b = MediaButtonWithText(
                        pic=type_img(device['type']),
                        ltext=device['name'],
                        device=device,
                        width=w,
                        size_hint=(None, 1))
                self.medias.add_widget(b)
        else:
            return
        self._devices.append(device['uid'])


class Shutters(Screen):
    pass


class Scenarios(Screen):
    pass


class RoomButton(Button):
    pic = StringProperty()
    ltext = StringProperty()


class LightButtonWithText(ToggleButton):
    pic = StringProperty()
    ltext = StringProperty()


class MediaButtonWithText(ToggleButton):
    pic = StringProperty()
    ltext = StringProperty()
    device = ObjectProperty()


class Pop_device(object):

    def __init__(self, parent):
        self.parent = parent
        content = parent.typ(pop=self)
        self.popup = Popup(
            title=parent.name,
            content=content,
            size_hint=(.2, .3))

    def display(self):
        self.popup.open()

    def dismiss(self):
        self.popup.dismiss()

    def define_size(self, size):
        print('Size: %s' % size)
        if size[0] < 120:
            print('resize2 !')
            self.popup.size_hint = self.popup.size_hint[0] * 1.5,\
                self.popup.size_hint[1] * 1.5
#             self.popup.size = (100, 100)
#             self.popup.content.size = (100, 100)


class Bubble_device(Bubble):
    pass


class Player_menu(BoxLayout):
    pop = ObjectProperty()


class Light_menu(BoxLayout):
    pop = ObjectProperty()


class Bubble_player(Bubble):
    pass

# class SensorLabel(Label):


class SensorPad(Scatter):
    sensors = ListProperty([])

    def __init__(self, *args, **kwargs):
        super(SensorPad, self).__init__(*args, **kwargs)

    def on_sensors(self, instance, value):
        self.ids.bl.clear_widgets()
        for s in value:
            d, v, u = s.get()
            if u is None:
                l = Label(text='%s: %s' % (d, ('Oui' if v else 'Non')))
            else:
                l = Label(text='%s: %s %s' % (d, v, u))
            self.ids.bl.add_widget(l)
        self.size = (self.size[0], 40*len(value))
#         m = Matrix().scale(1, len(value), 1)
#         self.apply_transform(m, True)
            

class DeviceButton(Scatter):
    pic_true = StringProperty('data/icons/lamp_1.png')
    pic_false = StringProperty('data/icons/lamp_0.png')
    state = BooleanProperty(False)
    play = ObjectProperty(None)
    config = ObjectProperty(None)
    open = ObjectProperty(None)
    name = StringProperty('Light')
    bubble = ObjectProperty(None)
    scheduled = False
    typ = Light_menu

    def pushed(self):
        if self.do_translation_x:
            #print('unlocked')
            return True
        else:
            Clock.schedule_once(self.show_bubble, 1)
            self.scheduled = True

    def on_touch_up(self, touch):
        if self.scheduled:
            Clock.unschedule(self.show_bubble)
            self.scheduled = False
            #print('locked')
            self.state = not self.state
            self.play(self)
        if self.do_translation_x:
            #print('locking')
            self.do_translation_x = False
            self.do_translation_y = False
            if self.config:
                self.config.set(
                    self.name,
                    'position',
                    str(self.pos[0])+'*'+str(self.pos[1]))
                self.config.write()
                
    def unlock(self):
        #print('unlock')
        self.do_translation_x = True
        self.do_translation_y = True
#         self.unlocked = True
#         self.remove_widget(self.bubb)
#         return False

    def show_bubble(self, *l):
        self.scheduled = False
#         self.bubb = bubb = self.bubble()
        #bubb.pos = bubb.pos[0] + self.width, bubb.pos[1]
        if not self.bubble:
            self.bubble = Pop_device(self)
        self.bubble.display()
#         self.add_widget(bubb)

#     def on_touch_down(self, touch):
# #         print('touch %s - %s' % (touch.pos, self.pos))
#         
#         '''.. versionchanged:: 1.4.0'''
#         if self.collide_point(*touch.pos):
#             self.state = not self.state
#             print(self.state)
#             return self.play(self)
#             if self.locked:
#                 return True

class LightButton(DeviceButton):
    pass


class PlayerButton(DeviceButton):
    pic_true = StringProperty('data/icons/multimedia_playing')
    pic_false = StringProperty('data/icons/multimedia_stopped.png')
    typ = Player_menu
#     bubble = Pop_device(self)


class ScatterCross(Scatter):
    pass


class HVAC(Screen):
    pass


class BgImage(Image):
    pass


class SettingImg(SettingPath):

    def _create_popup(self, instance):
        from jnius import autoclass  # SDcard Android

        # Get path to SD card Android
        try:
            Environment = autoclass('android.os.Environment')
#             print(Environment.DIRECTORY_DCIM)
#             print(Environment.DIRECTORY_MOVIES)
#             print(Environment.DIRECTORY_MUSIC)
            env = Environment()
            print('two')
            sdpath = env.getExternalStorageDirectory().getAbsolutePath()
            try:
                if not env.isExternalStorageRemovable():
                    if os.path.lexists('/storage/sdcard1'):
                        sdpath = '/storage/sdcard1/'\
                            + Environment.DIRECTORY_PICTURES
                else:
                    print('removable')
            except Exception as err:
                print(err)
            print('three')
            print(':)')

        # Not on Android
        except:
            print(':(')
            sdpath = os.path.expanduser('~')
        print('popup!')
        print(sdpath)
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing=5)
#         popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, 0.9),
            width=dp(300))

        # create the filechooser
        print('1')
        if os.path.isfile(self.value):
            print('file!')
            path = os.path.split(self.value)[0]
            if len(sdpath) == 0:
                path = os.path.expanduser('~')
            elif '/data/living.png' in self.value:
                print('living found!')
                path = sdpath
        else:
            path = sdpath
        print(path)
        self.textinput = textinput = FileChooserListView(
            path=path, size_hint=(1, 1), dirselect=True)
        textinput.bind(on_path=self._validate)
        self.textinput = textinput

        # construct the content
        content.add_widget(textinput)
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()


class SettingPos(SettingString):
    '''Implementation of a string setting on top of a :class:`SettingItem`.
    It is visualized with a :class:`~kivy.uix.label.Label` widget that, when
    clicked, will open a :class:`~kivy.uix.popup.Popup` with a
    :class:`~kivy.uix.textinput.Textinput` so the user can enter a custom
    value.
    '''

    popup = ObjectProperty(None, allownone=True)
    '''(internal) Used to store the current popup when it's shown.

    :attr:`popup` is an :class:`~kivy.properties.ObjectProperty` and defaults
    to None.
    '''

#     position = ObjectProperty(None)
    '''(internal) Used to store the current textinput from the popup and
    to listen for changes.

    :attr:`textinput` is an :class:`~kivy.properties.ObjectProperty` and
    defaults to None.
    '''
    pic = StringProperty()
    position = StringProperty('50*50')

    def __init__(self, **kwargs):
        super(SettingPos, self).__init__(**kwargs)
        self.img = Image(source=self.pic)

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _dismiss(self, *largs):
        if self.popup:
            self.popup.dismiss()
        self.popup = None

    def _register(self, instance, touch):
        if self.img.collide_point(*touch.pos):
            #             self.position = '*'.join([str(p) for p in touch.pos])
            #             print(touch)
            #             print(self.img.pos)
            #             print(self.img.size)
            #             print(Window.size)
            x, y = self.img.to_widget(touch.pos[0], touch.pos[1], True)
            x = x - self.img.pos[0] - 20.0
            y = y + 68.0
#             print('%s * %s' % (x, y))
            self.position = str(x)+'*'+str(y)

    def _validate(self, instance):
        value = self.position
        self.value = value
#         print(self.value)
        self._dismiss()

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
#         popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content)
        pos = [float(c) for c in self.value.split('*')]
        scat = ScatterCross(size=(20, 20), size_hint=(None, None), pos=pos)
        scat.bind(on_touch_up=self._register)
        self.img.add_widget(scat)
        content.add_widget(self.img)
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()
        
        
def type_img(typ):
    if typ in ['Lights']:
        return 'data/icons/lamp_1.png'
    elif typ in ['MediaPlayer']:
        return 'data/icons/Multimedia.png'
